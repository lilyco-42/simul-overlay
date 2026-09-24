// 普惠同传 - 悬浮字幕壳
// Python 管线子进程承载四路功能：麦克风同传 / 系统声音同传 / 圈选OCR / 整篇阅读。
// stdout 行分流：`[xxx]` 状态行 → status 事件；字幕行 → subtitle 事件；stderr → status。
//
// 两种运行模式（运行时探测，勿混淆）：
//   打包模式（M4 离线全量包）：resources/simul-pipe/simul-pipe[.exe] + resources/models，
//     子进程为侧车子命令（system/mic/ocr/read），自动注入 SIMUL_MODEL_DIR / ARGOS_PACKAGES_DIR。
//   开发模式：SIMUL_PYTHON + 仓库脚本（SIMUL_DEMO* / SIMUL_SCRIPT_DIR 可覆盖），现状不变。
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Emitter;
use tauri::Manager;

fn py_path() -> String {
    std::env::var("SIMUL_PYTHON")
        .unwrap_or_else(|_| r"D:\Code\simul-demo\.venv\Scripts\python.exe".into())
}

/// 脚本定位：SIMUL_SCRIPT_DIR 可整体重定向（打包分发用），否则用开发目录。
fn script_path(name: &str) -> String {
    match std::env::var("SIMUL_SCRIPT_DIR") {
        Ok(dir) => format!(r"{dir}\{name}"),
        Err(_) => format!(r"D:\Code\simul-demo\{name}"),
    }
}

/// 打包模式侧车：exe 路径 + 随包 models 根（可缺省，仅翻译不建 recognizer 时仍可用）。
struct Sidecar {
    exe: PathBuf,
    models: Option<PathBuf>,
}

/// 在 resource_dir 下探测 simul-pipe 侧车。
/// 候选布局兼容 Tauri 资源映射差异（直接 resources 根 / 再套一层 resources/）。
fn find_sidecar(app: &tauri::AppHandle) -> Option<Sidecar> {
    let res = app.path().resource_dir().ok()?;
    for base in [res.clone(), res.join("resources")] {
        for exe_name in ["simul-pipe.exe", "simul-pipe"] {
            let p = base.join("simul-pipe").join(exe_name);
            if p.exists() {
                let models = base.join("models");
                return Some(Sidecar {
                    exe: p,
                    models: models.exists().then_some(models),
                });
            }
        }
    }
    None
}

/// 组装子进程命令：
/// - 打包模式：`<sidecar> <sub> [args...]` + 随包模型 env；
/// - 开发模式：`SIMUL_PYTHON <dev_script> [args...]`。
/// 共同附加 stdout/stderr 管道与 null stdin。
fn build_command(
    app: &tauri::AppHandle,
    sub: &str,
    dev_script: String,
    args: &[String],
) -> Result<Command, String> {
    let mut cmd = if let Some(sc) = find_sidecar(app) {
        let mut c = Command::new(&sc.exe);
        c.arg(sub);
        if let Some(m) = &sc.models {
            c.env("SIMUL_MODEL_DIR", m);
            let argos = m.join("argos-packages");
            if argos.exists() {
                c.env("ARGOS_PACKAGES_DIR", argos);
            }
        }
        c
    } else {
        let mut c = Command::new(py_path());
        c.arg(dev_script);
        c
    };
    for a in args {
        cmd.arg(a);
    }
    cmd.stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .stdin(Stdio::null());
    Ok(cmd)
}

#[derive(Default)]
struct Slots {
    audio: Option<Child>,
    ocr: Option<Child>,
    doc: Option<Child>,
}

fn kill(slot: &mut Option<Child>) {
    if let Some(mut c) = slot.take() {
        let _ = c.kill();
        let _ = c.wait();
    }
}

/// 把子进程 stdout/stderr 接到前端事件流。
fn stream(app: &tauri::AppHandle, child: &mut Child) {
    if let Some(out) = child.stdout.take() {
        let app = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(out).lines().map_while(Result::ok) {
                let t = line.trim_end().to_string();
                if t.is_empty() {
                    continue;
                }
                if t.starts_with('[') {
                    let _ = app.emit("status", t);
                } else {
                    let _ = app.emit("subtitle", t);
                }
            }
        });
    }
    if let Some(err) = child.stderr.take() {
        let app = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(err).lines().map_while(Result::ok) {
                let t = line.trim_end().to_string();
                if !t.is_empty() {
                    let _ = app.emit("status", format!("[err] {t}"));
                }
            }
        });
    }
}

#[tauri::command]
fn start_pipeline(
    app: tauri::AppHandle,
    state: tauri::State<'_, Mutex<Slots>>,
    source: String,
    tts: bool,
    seconds: u64,
) -> Result<(), String> {
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.audio);

    let is_system = source == "system";
    let sub = if is_system { "system" } else { "mic" };
    let script = if is_system {
        std::env::var("SIMUL_DEMO_SYSTEM").unwrap_or_else(|_| script_path("demo_system.py"))
    } else {
        std::env::var("SIMUL_DEMO").unwrap_or_else(|_| script_path("demo_mic.py"))
    };

    let mut cmd = build_command(&app, sub, script, &[seconds.to_string()])?;
    cmd.env("SIMUL_TTS", if tts { "1" } else { "0" });

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    stream(&app, &mut child);
    slots.audio = Some(child);
    Ok(())
}

#[tauri::command]
fn start_ocr(
    app: tauri::AppHandle,
    state: tauri::State<'_, Mutex<Slots>>,
    select: bool,
) -> Result<(), String> {
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.ocr);

    let script = std::env::var("SIMUL_OCR").unwrap_or_else(|_| script_path("demo_ocr.py"));
    let mut args: Vec<String> = Vec::new();
    if select {
        args.push("--select".into());
    }
    let mut cmd = build_command(&app, "ocr", script, &args)?;

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    stream(&app, &mut child);
    slots.ocr = Some(child);
    Ok(())
}

#[tauri::command]
fn read_doc(
    app: tauri::AppHandle,
    state: tauri::State<'_, Mutex<Slots>>,
    path: String,
    dst: String,
) -> Result<(), String> {
    if !std::path::Path::new(&path).exists() {
        return Err(format!("文件不存在: {path}"));
    }
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.doc);

    let script = std::env::var("SIMUL_READ").unwrap_or_else(|_| script_path("read_doc.py"));
    let mut args: Vec<String> = vec![path];
    if !dst.is_empty() {
        args.push(dst);
    }
    let mut cmd = build_command(&app, "read", script, &args)?;

    let mut child = cmd.spawn().map_err(|e| e.to_string())?;
    stream(&app, &mut child);
    slots.doc = Some(child);
    Ok(())
}

#[tauri::command]
fn stop_all(state: tauri::State<'_, Mutex<Slots>>) -> Result<(), String> {
    let mut slots = state.lock().map_err(|e| e.to_string())?;
    kill(&mut slots.audio);
    kill(&mut slots.ocr);
    kill(&mut slots.doc);
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(Mutex::new(Slots::default()))
        .invoke_handler(tauri::generate_handler![
            start_pipeline,
            start_ocr,
            read_doc,
            stop_all
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
