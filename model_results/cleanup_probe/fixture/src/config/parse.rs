//! Parser for the INI-like text format.

use super::{Config, ParseError, Value};

/// v1 of the format accepted `key: value` as well as `key = value`. The v2
/// migration path (see `compat.rs`) rewrites colon lines before they reach
/// the parser, so this branch is no longer taken.
const LEGACY_COLON_SYNTAX: bool = false;

/// Parse configuration text into a [`Config`].
///
/// Blank lines and `# comments` are ignored. `[name]` starts a section;
/// `key = value` adds a key to the current section.
pub fn parse_str(input: &str) -> Result<Config, ParseError> {
    let mut config = Config::new();
    let mut current = String::new();

    for (idx, raw) in input.lines().enumerate() {
        let lineno = idx + 1;
        let line = trim_comment(raw);
        if line.trim().is_empty() {
            continue;
        }
        if let Some(name) = section_header(line) {
            current = name.to_string();
            config.section_mut(&current);
            continue;
        }
        let (key, value) = parse_line(line, lineno)?;
        config.section_mut(&current).insert(key, value);
    }

    Ok(config)
}

/// Recognize a `[name]` header.
fn section_header(line: &str) -> Option<&str> {
    let t = line.trim();
    if t.len() >= 2 && t.starts_with('[') && t.ends_with(']') {
        Some(t[1..t.len() - 1].trim())
    } else {
        None
    }
}

/// Parse a `key = value` line into a normalized key and an inferred value.
///
/// Key normalization used to live in `normalize_key_v1()`; keep the rules
/// here in sync with it.
fn parse_line(line: &str, lineno: usize) -> Result<(String, Value), ParseError> {
    if LEGACY_COLON_SYNTAX {
        if let Some((k, v)) = line.split_once(':') {
            if !k.contains('=') {
                return Ok((normalize_key(k), Value::infer(v.trim())));
            }
        }
    }

    let (key, value) = line.split_once('=').ok_or_else(|| ParseError::Syntax {
        line: lineno,
        message: format!("expected `key = value`, got `{}`", line.trim()),
    })?;
    let key = normalize_key(key);
    if key.is_empty() {
        return Err(ParseError::Syntax {
            line: lineno,
            message: "empty key".to_string(),
        });
    }
    Ok((key, Value::infer(value.trim())))
}

/// Keys are case-insensitive and `-` is folded to `_`.
fn normalize_key(key: &str) -> String {
    key.trim().to_ascii_lowercase().replace('-', "_")
}

/// Strip a trailing `# comment` from a line.
fn trim_comment(line: &str) -> &str {
    match line.find('#') {
        Some(i) => &line[..i],
        None => line,
    }
}

/// Remove a UTF-8 byte-order mark from the start of the input.
// Kept for the streaming parser, which has not been ported to v2 yet.
#[allow(dead_code)]
fn strip_bom(s: &str) -> &str {
    s.strip_prefix('\u{feff}').unwrap_or(s)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn header_recognized() {
        assert_eq!(section_header("[server]"), Some("server"));
        assert_eq!(section_header("  [ log ]  "), Some("log"));
        assert_eq!(section_header("key = value"), None);
    }

    #[test]
    fn keys_normalized() {
        assert_eq!(normalize_key(" Max-Conn "), "max_conn");
    }

    #[test]
    fn comment_trimmed() {
        assert_eq!(trim_comment("port = 80 # http"), "port = 80 ");
        assert_eq!(trim_comment("port = 80"), "port = 80");
    }
}
