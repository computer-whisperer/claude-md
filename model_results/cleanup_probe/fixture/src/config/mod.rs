//! Configuration model: named sections of key/value pairs.

pub mod compat;
pub mod parse;
pub mod value;

use std::collections::BTreeMap;
use std::fmt;
use std::path::Path;

pub use value::Value;

/// A named group of keys.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Section {
    entries: BTreeMap<String, Value>,
}

impl Section {
    /// Look up a key in this section.
    pub fn get(&self, key: &str) -> Option<&Value> {
        self.entries.get(key)
    }

    /// Insert or replace a key.
    pub fn insert(&mut self, key: impl Into<String>, value: Value) {
        self.entries.insert(key.into(), value);
    }

    /// Number of keys in the section.
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// True if the section has no keys.
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Iterate keys in sorted order.
    pub fn iter(&self) -> impl Iterator<Item = (&String, &Value)> {
        self.entries.iter()
    }
}

/// A parsed configuration. Keys that appear before any `[section]` header
/// land in the section named `""`.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Config {
    sections: BTreeMap<String, Section>,
}

impl Config {
    /// An empty configuration.
    pub fn new() -> Self {
        Self::default()
    }

    /// Read and parse a file.
    pub fn load(path: impl AsRef<Path>) -> Result<Config, ParseError> {
        let text = std::fs::read_to_string(path.as_ref())
            .map_err(|e| ParseError::Io(e.to_string()))?;
        parse::parse_str(&text)
    }

    /// Look up a section by name.
    pub fn section(&self, name: &str) -> Option<&Section> {
        self.sections.get(name)
    }

    /// Get a section, creating it if absent.
    pub fn section_mut(&mut self, name: &str) -> &mut Section {
        self.sections.entry(name.to_string()).or_default()
    }

    /// Look up `key` in `section`.
    pub fn get(&self, section: &str, key: &str) -> Option<&Value> {
        self.section(section)?.get(key)
    }

    /// Iterate sections in sorted order.
    pub fn sections(&self) -> impl Iterator<Item = (&String, &Section)> {
        self.sections.iter()
    }

    /// Overlay `other` onto `self`; keys in `other` win.
    pub fn merge(&mut self, other: Config) {
        for (name, section) in other.sections {
            let dst = self.section_mut(&name);
            for (key, value) in section.entries {
                dst.insert(key, value);
            }
        }
    }
}

/// Errors from reading or parsing configuration.
#[derive(Debug, Clone, PartialEq)]
pub enum ParseError {
    /// The file could not be read.
    Io(String),
    /// A line did not match the expected syntax.
    Syntax { line: usize, message: String },
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::Io(msg) => write!(f, "io error: {msg}"),
            ParseError::Syntax { line, message } => write!(f, "line {line}: {message}"),
        }
    }
}

impl std::error::Error for ParseError {}
