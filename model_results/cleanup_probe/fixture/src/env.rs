//! Environment-variable overlay.
//!
//! Variables named `PREFIX__SECTION__KEY` override `key` in `[section]`.
//! With the default prefix, `APP__SERVER__PORT=9090` sets `[server] port`.

use crate::config::{Config, Value};
use crate::util::{is_blank_line, split_kv, strip_comment};

/// Prefix used by [`overlay`].
pub const DEFAULT_PREFIX: &str = "APP";

/// Apply overrides from an explicit list of `(name, value)` pairs.
pub fn overlay_from<I>(config: &mut Config, prefix: &str, vars: I)
where
    I: IntoIterator<Item = (String, String)>,
{
    let marker = format!("{prefix}__");
    for (name, raw) in vars {
        let Some(rest) = name.strip_prefix(&marker) else {
            continue;
        };
        let Some((section, key)) = rest.split_once("__") else {
            continue;
        };
        let value = Value::infer(strip_comment(&raw).trim());
        config
            .section_mut(&section.to_ascii_lowercase())
            .insert(key.to_ascii_lowercase(), value);
    }
}

/// Apply overrides from the process environment using `prefix`.
pub fn overlay(config: &mut Config, prefix: &str) {
    overlay_from(config, prefix, std::env::vars());
}

/// Parse `KEY=VALUE` lines (a `.env` file) into pairs suitable for
/// [`overlay_from`]. Blank lines and `# comments` are skipped.
pub fn parse_dotenv(text: &str) -> Vec<(String, String)> {
    text.lines()
        .filter(|l| !is_blank_line(l))
        .map(strip_comment)
        .filter(|l| !l.is_empty())
        .filter_map(|l| split_kv(l).map(|(k, v)| (k.to_string(), v.to_string())))
        .collect()
}
