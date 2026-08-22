//! Small string helpers shared across modules.

/// Returns true if the line is empty or whitespace-only.
pub(crate) fn is_blank_line(line: &str) -> bool {
    line.trim().is_empty()
}

/// Strip a trailing `# comment` from a line, along with any whitespace
/// before it.
pub(crate) fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(i) => line[..i].trim_end(),
        None => line.trim_end(),
    }
}

/// Split `KEY=VALUE` at the first `=`, trimming both sides.
pub(crate) fn split_kv(s: &str) -> Option<(&str, &str)> {
    s.split_once('=').map(|(k, v)| (k.trim(), v.trim()))
}
