use confkit::env::{overlay_from, parse_dotenv, DEFAULT_PREFIX};
use confkit::{parse_str, Value};

#[test]
fn overlay_overrides_matching_keys() {
    let mut c = parse_str("[server]\nport = 8080\nhost = localhost\n").unwrap();
    let vars = vec![
        ("APP__SERVER__PORT".to_string(), "9090".to_string()),
        ("APP__LOG__LEVEL".to_string(), "debug".to_string()),
        ("OTHER__SERVER__PORT".to_string(), "1".to_string()),
        ("APP__NOSEP".to_string(), "ignored".to_string()),
    ];
    overlay_from(&mut c, DEFAULT_PREFIX, vars);
    assert_eq!(c.get("server", "port"), Some(&Value::Int(9090)));
    assert_eq!(c.get("server", "host").unwrap().as_str(), Some("localhost"));
    assert_eq!(c.get("log", "level").unwrap().as_str(), Some("debug"));
    assert!(c.section("nosep").is_none());
}

#[test]
fn dotenv_parses_pairs() {
    let pairs = parse_dotenv("# comment\nA=1\n\nB = two # trailing\nnot a pair\n");
    assert_eq!(
        pairs,
        vec![
            ("A".to_string(), "1".to_string()),
            ("B".to_string(), "two".to_string())
        ]
    );
}
