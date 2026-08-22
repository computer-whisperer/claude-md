use std::time::{Duration, SystemTime};

use confkit::watch::Watcher;

fn temp_file(name: &str, contents: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!("confkit-watch-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join(name);
    std::fs::write(&path, contents).unwrap();
    path
}

#[test]
fn first_poll_loads_then_quiet() {
    let path = temp_file("a.conf", "[s]\nk = 1\n");
    let mut w = Watcher::new(&path).with_interval(Duration::from_millis(10));
    assert_eq!(w.interval(), Duration::from_millis(10));
    let first = w.poll().unwrap().expect("first poll loads");
    assert_eq!(first.get("s", "k").unwrap().as_int(), Some(1));
    assert!(w.poll().unwrap().is_none());
}

#[test]
fn poll_detects_modification() {
    let path = temp_file("b.conf", "[s]\nk = 1\n");
    let mut w = Watcher::new(&path);
    w.poll().unwrap();
    std::fs::write(&path, "[s]\nk = 2\n").unwrap();
    // Push the mtime forward so coarse filesystem timestamps still differ.
    let later = SystemTime::now() + Duration::from_secs(2);
    std::fs::File::open(&path).unwrap().set_modified(later).unwrap();
    let reloaded = w.poll().unwrap().expect("change detected");
    assert_eq!(reloaded.get("s", "k").unwrap().as_int(), Some(2));
}
