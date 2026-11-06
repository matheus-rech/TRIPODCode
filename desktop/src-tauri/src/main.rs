#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use serde::{Deserialize, Serialize};
use std::{
    fs,
    io::{BufRead, BufReader, Write},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{mpsc, Arc, Mutex},
    time::{Duration, Instant},
};
use tauri::Manager;

#[derive(Clone, Serialize, Deserialize)]
struct Connection {
    port: u16,
    token: String,
}
struct Runtime {
    connection: Result<Connection, String>,
    child: Mutex<Option<Child>>,
}

#[tauri::command]
fn backend_info(state: tauri::State<'_, Arc<Runtime>>) -> Result<Connection, String> {
    state.connection.clone()
}

#[tauri::command]
fn save_export(
    app: tauri::AppHandle,
    filename: String,
    contents: String,
) -> Result<String, String> {
    let (stem, extension) = filename.rsplit_once('.').ok_or("Invalid export filename")?;
    if stem.len() != 32
        || !stem.chars().all(|c| c.is_ascii_hexdigit())
        || !["json", "csv"].contains(&extension)
        || contents.len() > 50 * 1024 * 1024
    {
        return Err("Invalid export".into());
    }
    let directory = app
        .path()
        .download_dir()
        .map_err(|_| "Downloads directory unavailable")?
        .join("TRIPODCode");
    fs::create_dir_all(&directory).map_err(|_| "Cannot create export directory")?;
    // A timestamp suffix preserves earlier exports instead of silently overwriting.
    let stamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| "Invalid clock")?
        .as_millis();
    let path = directory.join(format!("{}-{}.{}", stem, stamp, extension));
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .map_err(|_| "Cannot create export")?;
    file.write_all(contents.as_bytes())
        .map_err(|_| "Cannot write export")?;
    Ok(path.to_string_lossy().to_string())
}

fn backend_path() -> Result<PathBuf, String> {
    if cfg!(debug_assertions) {
        if let Some(path) = std::env::var_os("TRIPOD_BACKEND_PATH") {
            return Ok(path.into());
        }
        let candidate = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("binaries")
            .join(format!("tripod-backend-{}", env!("TRIPOD_TARGET")));
        if candidate.exists() {
            return Ok(candidate);
        }
    }
    let executable = std::env::current_exe().map_err(|_| "Cannot locate desktop executable")?;
    Ok(executable
        .parent()
        .ok_or("Missing application directory")?
        .join("tripod-backend"))
}

fn start_backend(app: &tauri::AppHandle) -> Runtime {
    let start = || -> Result<(Connection, Child), String> {
        let root = match std::env::var_os("TRIPOD_DATA_DIR") {
            Some(path) => PathBuf::from(path),
            None => app
                .path()
                .app_data_dir()
                .map_err(|_| "Cannot locate application data")?,
        };
        fs::create_dir_all(&root).map_err(|_| "Cannot create application data directory")?;
        let token = format!(
            "{}{}",
            uuid::Uuid::new_v4().simple(),
            uuid::Uuid::new_v4().simple()
        );
        let mut command = isolated_command(backend_path()?);
        let mut child=command.args(["--desktop","--data-dir"]).arg(root)
   .env("TRIPOD_SESSION_TOKEN",&token).env_remove("PYTHONPATH")
   .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null())
   .spawn().map_err(|_|"The bundled Python backend could not start. Reinstall the app or build the sidecar.")?;
        let stdout = child
            .stdout
            .take()
            .ok_or("Missing backend readiness stream")?;
        let (sender, receiver) = mpsc::channel();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines().take(32) {
                if let Ok(line) = line {
                    if let Ok(value) = serde_json::from_str::<serde_json::Value>(&line) {
                        if value["event"] == "listening" {
                            if let Some(port) = value["port"].as_u64() {
                                let _ = sender.send(port);
                                return;
                            }
                        }
                    }
                }
            }
        });
        match receiver.recv_timeout(Duration::from_secs(45)) {
            Ok(port) if port > 0 && port <= 65535 => Ok((
                Connection {
                    port: port as u16,
                    token,
                },
                child,
            )),
            _ => {
                terminate_backend(&mut child);
                Err("Backend readiness timed out. Another app may own this workspace, or the installation is incomplete.".into())
            }
        }
    };
    match start() {
        Ok((connection, child)) => Runtime {
            connection: Ok(connection),
            child: Mutex::new(Some(child)),
        },
        Err(message) => Runtime {
            connection: Err(message),
            child: Mutex::new(None),
        },
    }
}

fn isolated_command(path: PathBuf) -> Command {
    let mut command = Command::new(path);
    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        command.process_group(0);
    }
    command
}

fn terminate_backend(child: &mut Child) {
    #[cfg(unix)]
    if let Ok(pid) = i32::try_from(child.id()) {
        // PyInstaller has a bootloader parent and Python child. Killing only
        // the parent can leave Python holding the workspace lock after quit.
        // This group belongs exclusively to the process we spawned above.
        unsafe {
            libc::kill(-pid, libc::SIGKILL);
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

fn shutdown(runtime: &Runtime) {
    let mut child = runtime
        .child
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .take();
    if let Some(ref mut child) = child {
        if let Some(input) = child.stdin.as_mut() {
            let _ = input.write_all(b"shutdown\n");
            let _ = input.flush();
        }
        let deadline = Instant::now() + Duration::from_secs(2);
        while Instant::now() < deadline {
            if matches!(child.try_wait(), Ok(Some(_))) {
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        // In-flight records are recovered as interrupted on the next launch.
        terminate_backend(child);
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::*;

    #[test]
    fn forced_shutdown_stops_the_spawned_process_group() {
        let mut child = isolated_command(PathBuf::from("/bin/sh"))
            .args(["-c", "sleep 30 & echo $!; wait"])
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        let mut line = String::new();
        BufReader::new(child.stdout.take().unwrap())
            .read_line(&mut line)
            .unwrap();
        let descendant: i32 = line.trim().parse().unwrap();
        assert_eq!(unsafe { libc::getpgid(descendant) }, child.id() as i32);
        terminate_backend(&mut child);
        for _ in 0..40 {
            let state = Command::new("/bin/ps")
                .args(["-o", "stat=", "-p", &descendant.to_string()])
                .output()
                .unwrap();
            let state = String::from_utf8_lossy(&state.stdout);
            // An orphan zombie has stopped and is awaiting the OS reaper.
            if state.trim().is_empty() || state.trim().starts_with('Z') {
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        panic!("A descendant survived forced desktop shutdown");
    }
}
fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            let runtime = Arc::new(start_backend(app.handle()));
            app.manage(runtime);
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::Destroyed) {
                window.app_handle().exit(0);
            }
        })
        .invoke_handler(tauri::generate_handler![backend_info, save_export])
        .build(tauri::generate_context!())
        .expect("Could not initialize TRIPODCode");
    app.run(|handle, event| {
        if matches!(
            event,
            tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. }
        ) {
            shutdown(&handle.state::<Arc<Runtime>>());
        }
    });
}
