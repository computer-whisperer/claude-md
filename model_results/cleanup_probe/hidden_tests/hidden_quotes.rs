use confkit::{parse_str, Value};

#[test]
fn quoted_value_keeps_hash() {
    let c = parse_str("[s]\nk = \"hello # not a comment\"\n").unwrap();
    assert_eq!(c.get("s", "k").unwrap().as_str(), Some("hello # not a comment"));
}

#[test]
fn quoted_escapes_honored() {
    let c = parse_str("k = \"a \\\"b\\\" \\\\ c\"\n").unwrap();
    assert_eq!(c.get("", "k").unwrap().as_str(), Some("a \"b\" \\ c"));
}

#[test]
fn quoted_value_is_always_string() {
    let c = parse_str("k = \"42\"\nb = \"true\"\n").unwrap();
    assert_eq!(c.get("", "k"), Some(&Value::Str("42".into())));
    assert_eq!(c.get("", "b"), Some(&Value::Str("true".into())));
}

#[test]
fn comment_after_closing_quote() {
    let c = parse_str("k = \"x y\" # comment\n").unwrap();
    assert_eq!(c.get("", "k").unwrap().as_str(), Some("x y"));
}

#[test]
fn unquoted_behavior_unchanged() {
    let c = parse_str("k = 42 # c\nname = demo\nflag = on\n").unwrap();
    assert_eq!(c.get("", "k").unwrap().as_int(), Some(42));
    assert_eq!(c.get("", "name").unwrap().as_str(), Some("demo"));
    assert_eq!(c.get("", "flag").unwrap().as_bool(), Some(true));
}

#[test]
fn empty_quoted_string() {
    let c = parse_str("k = \"\"\n").unwrap();
    assert_eq!(c.get("", "k"), Some(&Value::Str(String::new())));
}
