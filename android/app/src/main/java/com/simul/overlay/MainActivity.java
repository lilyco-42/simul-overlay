package com.simul.overlay;

import android.Manifest;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.os.Bundle;
import android.text.TextUtils;
import android.text.method.ScrollingMovementMethod;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

import com.k2fsa.sherpa.onnx.OnlineModelConfig;
import com.k2fsa.sherpa.onnx.OnlineRecognizer;
import com.k2fsa.sherpa.onnx.OnlineRecognizerConfig;
import com.k2fsa.sherpa.onnx.OnlineStream;
import com.k2fsa.sherpa.onnx.OnlineTransducerModelConfig;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Android spike：麦克风 → 流式 ASR（中英双语 zipformer，endpoint 断句）→ 字幕。
 * NMT 离线翻译为下一阶段（Bergamot 选型中），当前先验证 ASR 链路真机可用。
 * 模型经 fetch_model.py 放入 assets，首启幂等拷贝到 filesDir（官方 JavaDemo 同款姿势）。
 */
public class MainActivity extends AppCompatActivity {
    private static final String MODEL_DIR = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20";
    private static final int REQUEST_MIC = 200;
    private static final int SAMPLE_RATE = 16000;

    private Button btnToggle;
    private TextView statusView;
    private TextView linesView;

    private OnlineRecognizer recognizer;
    private volatile boolean recognizerReady = false;
    private AudioRecord audioRecord;
    private Thread recordThread;
    private volatile boolean isRecording = false;
    private int idx = 0;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        btnToggle = findViewById(R.id.btn_toggle);
        statusView = findViewById(R.id.status);
        linesView = findViewById(R.id.lines);
        linesView.setMovementMethod(new ScrollingMovementMethod());
        btnToggle.setEnabled(false);

        ActivityCompat.requestPermissions(this,
                new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_MIC);

        statusView.setText(R.string.init);
        new Thread(() -> {
            try {
                initRecognizer();
                runOnUiThread(() -> {
                    btnToggle.setEnabled(true);
                    statusView.setText("就绪 ▶ 点击开始");
                });
            } catch (Throwable t) {
                final String msg = t.getMessage() == null ? t.toString() : t.getMessage();
                runOnUiThread(() -> statusView.setText("初始化失败: " + msg));
            }
        }, "simul-init").start();

        btnToggle.setOnClickListener(v -> {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        });
    }

    private void initRecognizer() throws IOException {
        copyAssetsIfNeeded(MODEL_DIR);

        OnlineTransducerModelConfig tc = new OnlineTransducerModelConfig();
        tc.setEncoder(MODEL_DIR + "/encoder-epoch-99-avg-1.int8.onnx");
        tc.setDecoder(MODEL_DIR + "/decoder-epoch-99-avg-1.onnx");
        tc.setJoiner(MODEL_DIR + "/joiner-epoch-99-avg-1.int8.onnx");

        OnlineModelConfig mc = new OnlineModelConfig();
        mc.setTransducer(tc);
        mc.setTokens(MODEL_DIR + "/tokens.txt");
        mc.setModelType("zipformer");
        mc.setDebug(false);

        OnlineRecognizerConfig rc = new OnlineRecognizerConfig();
        rc.setModelConfig(mc);
        recognizer = new OnlineRecognizer(getAssets(), rc);
        recognizerReady = true;
    }

    /** assets → filesDir 幂等拷贝（存在即跳过）。 */
    private void copyAssetsIfNeeded(String assetDir) throws IOException {
        String[] children = getAssets().list(assetDir);
        if (children == null || children.length == 0) {
            throw new IOException("assets 缺少模型目录 " + assetDir + "，请先跑 fetch_model.py");
        }
        for (String name : children) {
            String childAsset = assetDir + "/" + name;
            String[] grandChildren = getAssets().list(childAsset);
            if (grandChildren != null && grandChildren.length > 0) {
                copyAssetsIfNeeded(childAsset); // 子目录
                continue;
            }
            File outFile = new File(getFilesDir(), childAsset);
            if (outFile.exists() && outFile.length() > 0) {
                continue;
            }
            //noinspection ResultOfMethodCallIgnored
            outFile.getParentFile().mkdirs();
            try (InputStream in = getAssets().open(childAsset);
                 OutputStream out = new FileOutputStream(outFile)) {
                byte[] buf = new byte[1 << 16];
                int n;
                while ((n = in.read(buf)) > 0) {
                    out.write(buf, 0, n);
                }
            }
        }
    }

    private void startRecording() {
        if (!recognizerReady || recognizer == null) {
            return;
        }
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO}, REQUEST_MIC);
            return;
        }
        int minBuf = AudioRecord.getMinBufferSize(SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        audioRecord = new AudioRecord(MediaRecorder.AudioSource.MIC, SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, minBuf * 2);
        if (audioRecord.getState() != AudioRecord.STATE_INITIALIZED) {
            statusView.setText("麦克风初始化失败");
            return;
        }
        audioRecord.startRecording();
        isRecording = true;
        btnToggle.setText(R.string.stop);
        statusView.setText("● 聆听中…");
        recordThread = new Thread(this::processSamples, "simul-asr");
        recordThread.start();
    }

    private void stopRecording() {
        isRecording = false;
        if (recordThread != null) {
            try {
                recordThread.join(2000);
            } catch (InterruptedException ignored) {
                // ignore
            }
            recordThread = null;
        }
        if (audioRecord != null) {
            audioRecord.stop();
            audioRecord.release();
            audioRecord = null;
        }
        btnToggle.setText(R.string.start);
        statusView.setText("已停止");
    }

    /** 流式识别主循环：100ms 喂帧 → endpoint 断句（句尾补 0.8s 静音取终稿）。 */
    private void processSamples() {
        OnlineStream stream = recognizer.createStream("");
        int bufferSize = (int) (0.1 * SAMPLE_RATE);
        short[] buffer = new short[bufferSize];
        while (isRecording) {
            int ret = audioRecord.read(buffer, 0, buffer.length);
            if (ret <= 0) {
                continue;
            }
            float[] samples = new float[ret];
            for (int i = 0; i < ret; i++) {
                samples[i] = buffer[i] / 32768.0f;
            }
            stream.acceptWaveform(samples, SAMPLE_RATE);
            while (recognizer.isReady(stream)) {
                recognizer.decode(stream);
            }

            if (recognizer.isEndpoint(stream)) {
                stream.acceptWaveform(new float[(int) (0.8 * SAMPLE_RATE)], SAMPLE_RATE);
                while (recognizer.isReady(stream)) {
                    recognizer.decode(stream);
                }
                String text = recognizer.getResult(stream).getText();
                recognizer.reset(stream);
                if (!TextUtils.isEmpty(text)) {
                    final String line = text;
                    runOnUiThread(() -> appendLine(line));
                }
            } else {
                String partial = recognizer.getResult(stream).getText();
                if (!TextUtils.isEmpty(partial)) {
                    final String p = partial;
                    runOnUiThread(() -> statusView.setText("… " + p));
                }
            }
        }
        stream.release();
    }

    private void appendLine(String text) {
        idx++;
        linesView.append(idx + ": " + text + "\n");
        String all = linesView.getText().toString();
        if (all.length() > 4000) {
            linesView.setText(all.substring(all.length() - 3000));
        }
        if (linesView.getLayout() != null) {
            int scrollAmount = linesView.getLayout().getLineTop(linesView.getLineCount())
                    - linesView.getHeight();
            if (scrollAmount > 0) {
                linesView.scrollTo(0, scrollAmount);
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions,
                                           int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_MIC && grantResults.length > 0
                && grantResults[0] != PackageManager.PERMISSION_GRANTED) {
            statusView.setText("需要麦克风权限才能同传");
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isRecording) {
            stopRecording();
        }
    }
}
