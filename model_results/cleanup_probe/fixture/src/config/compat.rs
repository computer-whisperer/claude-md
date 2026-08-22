//! Transitional helpers for the v1 file format, which accepted
//! `key: value` lines.
//!
//! v1 callers should migrate to [`parse_str`](super::parse::parse_str).
//! Remove this module once the migration is complete.

use super::parse::parse_str;
use super::{Config, ParseError};

/// Returns true if the text looks like a v1 file: at least one non-comment,
/// non-header line that uses `:` rather than `=`.
pub fn is_legacy_format(input: &str) -> bool {
    input
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#') && !l.starts_with('['))
        .any(|l| !l.contains('=') && l.contains(':'))
}

/// Parse a v1 file by rewriting `key: value` lines to `key = value` and
/// delegating to the v2 parser.
pub fn parse_legacy(input: &str) -> Result<Config, ParseError> {
    let rewritten: Vec<String> = input
        .lines()
        .map(|l| {
            let t = l.trim_start();
            if t.starts_with('[') || t.starts_with('#') || t.contains('=') {
                return l.to_string();
            }
            match l.split_once(':') {
                Some((k, v)) => format!("{} = {}", k.trim_end(), v.trim_start()),
                None => l.to_string(),
            }
        })
        .collect();
    parse_str(&rewritten.join("\n"))
}
