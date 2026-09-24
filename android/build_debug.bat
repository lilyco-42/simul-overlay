@echo off
rem 本机构建 APK（带代理给 gradle wrapper 下载与依赖解析）；CI 不用此脚本。
set GRADLE_OPTS=-Dhttps.proxyHost=127.0.0.1 -Dhttps.proxyPort=7897 -Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=7897
cd /d %~dp0
call gradlew.bat %*
