use confkit::{parse_str, Config, ParseError, Value};

const SAMPLE: &str = "\
# top-level keys
name = demo

[server]
host = 0.0.0.0
port = 8080   # http
Max-Conn = 64

[log]
level = info
verbose = yes
ratio = 0.25
";

#[test]
fn parses_sections_and_keys() {
    let c = parse_str(SAMPLE).unwrap();
    assert_eq!(c.get("", "name").unwrap().as_str(), Some("demo"));
    assert_eq!(c.get("server", "host").unwrap().as_str(), Some("0.0.0.0"));
    assert_eq!(c.get("server", "port").unwrap().as_int(), Some(8080));
    assert_eq!(c.get("server", "max_conn").unwrap().as_int(), Some(64));
    assert_eq!(c.get("log", "level").unwrap().as_str(), Some("info"));
    assert_eq!(c.get("log", "verbose").unwrap().as_bool(), Some(true));
    assert_eq!(c.get("log", "ratio").unwrap().as_float(), Some(0.25));
}

#[test]
fn comments_and_blank_lines_ignored() {
    let c = parse_str("# only a comment\n\n   \n[a]\nx = 1 # trailing\n").unwrap();
    assert_eq!(c.get("a", "x"), Some(&Value::Int(1)));
    assert_eq!(c.section("a").unwrap().len(), 1);
}

#[test]
fn empty_section_exists() {
    let c = parse_str("[empty]\n").unwrap();
    assert!(c.section("empty").unwrap().is_empty());
}

#[test]
fn syntax_error_reports_line() {
    let err = parse_str("[a]\nx = 1\nthis is not a pair\n").unwrap_err();
    assert_eq!(
        err,
        ParseError::Syntax {
            line: 3,
            message: "expected `key = value`, got `this is not a pair`".into()
        }
    );
}

#[test]
fn empty_key_rejected() {
    assert!(matches!(
        parse_str(" = 1\n"),
        Err(ParseError::Syntax { line: 1, .. })
    ));
}

#[test]
fn later_keys_override_earlier() {
    let c = parse_str("[a]\nx = 1\nx = 2\n").unwrap();
    assert_eq!(c.get("a", "x"), Some(&Value::Int(2)));
}

#[test]
fn merge_overlays_keys() {
    let mut base = parse_str("[a]\nx = 1\ny = 2\n").unwrap();
    let over = parse_str("[a]\ny = 3\n[b]\nz = 4\n").unwrap();
    base.merge(over);
    assert_eq!(base.get("a", "x"), Some(&Value::Int(1)));
    assert_eq!(base.get("a", "y"), Some(&Value::Int(3)));
    assert_eq!(base.get("b", "z"), Some(&Value::Int(4)));
}

#[test]
fn load_reads_file() {
    let dir = std::env::temp_dir().join(format!("confkit-load-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("app.conf");
    std::fs::write(&path, "[s]\nk = v\n").unwrap();
    let c = Config::load(&path).unwrap();
    assert_eq!(c.get("s", "k").unwrap().as_str(), Some("v"));
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn display_of_values() {
    assert_eq!(Value::infer("42").to_string(), "42");
    assert_eq!(Value::infer("off").to_string(), "false");
    assert_eq!(Value::infer("hello").to_string(), "hello");
}
