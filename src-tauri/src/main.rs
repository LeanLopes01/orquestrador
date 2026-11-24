#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::Mutex;
use std::process::{Child,Command,Stdio};
use std::net::TcpStream;
use std::io::{Read,Write};
use std::time::Duration;
use tauri::Manager;
#[cfg(windows)]
use std::os::windows::process::CommandExt;

struct Runtime(Mutex<Option<Child>>);

fn shutdown() -> bool {
    let Ok(mut stream)=TcpStream::connect_timeout(&"127.0.0.1:1420".parse().unwrap(),Duration::from_secs(2)) else {return true;};
    let _=stream.set_read_timeout(Some(Duration::from_secs(50)));
    if stream.write_all(b"POST /api/system/exit HTTP/1.1\r\nHost: 127.0.0.1:1420\r\nX-Orchestrator-Request: 1\r\nContent-Length: 0\r\nConnection: close\r\n\r\n").is_err(){return false;}
    let mut response=String::new();
    stream.read_to_string(&mut response).is_ok() && response.starts_with("HTTP/1.1 200")
}

fn main() {
    tauri::Builder::default()
        .manage(Runtime(Mutex::new(None)))
        .setup(|app| {
            if cfg!(debug_assertions) {return Ok(());}
            if TcpStream::connect_timeout(&"127.0.0.1:1420".parse().unwrap(),Duration::from_millis(500)).is_ok(){
                return Err("A porta 1420 já está em uso. Feche a outra interface antes de abrir o Jarvis.".into());
            }
            let raw_res=app.path().resource_dir()?;
            let root=std::path::PathBuf::from(raw_res.to_string_lossy().trim_start_matches(r"\\?\")).join("runtime");
            let mut command=Command::new(root.join("node.exe"));
            command.arg(root.join("services").join("server.mjs")).arg("--with-helper").stdout(Stdio::null()).stderr(Stdio::null());
            command.env("JARVIS_WORKSPACE", std::env::var("JARVIS_WORKSPACE").unwrap_or_else(|_| std::path::Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_string_lossy().into_owned()));
            command.env("JARVIS_PARENT_PID", std::process::id().to_string());
            #[cfg(windows)] command.creation_flags(0x08000000);
            let child=command.spawn()?;
            *app.state::<Runtime>().0.lock().unwrap()=Some(child);
            let mut ready=false;
            for _ in 0..100 {
                if TcpStream::connect_timeout(&"127.0.0.1:1420".parse().unwrap(),Duration::from_millis(100)).is_ok(){ready=true;break;}
                std::thread::sleep(Duration::from_millis(100));
            }
            if !ready {return Err("O serviço local não iniciou na porta 1420.".into());}
            if let Some(window)=app.get_webview_window("main") {window.navigate("http://127.0.0.1:1420/#home".parse()?)?;}
            Ok(())
        })
        .on_window_event(|window,event| {
            if cfg!(debug_assertions){return;}
            if let tauri::WindowEvent::CloseRequested{api,..}=event {
                api.prevent_close();
                let app=window.app_handle().clone();
                let label=window.label().to_string();
                std::thread::spawn(move||{
                    if shutdown(){
                        if let Some(mut child)=app.state::<Runtime>().0.lock().unwrap().take(){let _=child.wait();}
                        app.exit(0);
                    }else if let Some(window)=app.get_webview_window(&label){
                        let _=window.set_title("Jarvis — tarefa ativa: cancele ou aguarde antes de sair");
                        let _=window.navigate("http://127.0.0.1:1420/#projects".parse().unwrap());
                    }
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("Não foi possível iniciar o Jarvis");
}
