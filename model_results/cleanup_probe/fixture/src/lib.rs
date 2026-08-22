//! confkit — a small layered configuration loader.
//!
//! Files use a simple INI-like format:
//!
//! ```text
//! [server]
//! host = 0.0.0.0
//! port = 8080        # trailing comments are allowed
//!
//! [log]
//! level = info
//! ```
//!
//! A file is parsed with [`parse_str`] or [`Config::load`], then optionally
//! overlaid with environment variables ([`env`]) and watched for changes
//! ([`watch`]).

pub mod config;
pub mod env;
pub mod watch;
mod util;

pub use config::compat::{is_legacy_format, parse_legacy};
pub use config::parse::parse_str;
pub use config::{Config, ParseError, Section, Value};
