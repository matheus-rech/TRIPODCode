fn main() {
    println!(
        "cargo:rustc-env=TRIPOD_TARGET={}",
        std::env::var("TARGET").unwrap()
    );
    tauri_build::build();
}
