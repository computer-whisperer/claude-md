//! Poll a configuration file for changes and reload it.

use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

use crate::config::{Config, ParseError};

/// Default polling interval.
pub const DEFAULT_INTERVAL: Duration = Duration::from_millis(500);

/// Tracks a file's modification time and reloads it when it changes.
#[derive(Debug)]
pub struct Watcher {
    path: PathBuf,
    last_modified: Option<SystemTime>,
    interval: Duration,
}

impl Watcher {
    /// Watch `path`. The first call to [`poll`](Self::poll) always reloads.
    pub fn new(path: impl Into<PathBuf>) -> Self {
        Watcher {
            path: path.into(),
            last_modified: None,
            interval: DEFAULT_INTERVAL,
        }
    }

    /// Set the polling interval reported by [`interval`](Self::interval).
    pub fn with_interval(mut self, interval: Duration) -> Self {
        self.interval = interval;
        self
    }

    /// The suggested delay between calls to [`poll`](Self::poll).
    pub fn interval(&self) -> Duration {
        self.interval
    }

    /// The watched path.
    pub fn path(&self) -> &Path {
        &self.path
    }

    /// Check the file's modification time. If it changed since the last
    /// call (or this is the first call), reload and return the new config.
    pub fn poll(&mut self) -> Result<Option<Config>, ParseError> {
        let modified = modified_time(&self.path)?;
        if self.last_modified == Some(modified) {
            return Ok(None);
        }
        let config = Config::load(&self.path)?;
        self.last_modified = Some(modified);
        Ok(Some(config))
    }
}

fn modified_time(path: &Path) -> Result<SystemTime, ParseError> {
    std::fs::metadata(path)
        .and_then(|m| m.modified())
        .map_err(|e| ParseError::Io(e.to_string()))
}

/// Poll once using the pre-0.3 free-function signature. Prefer
/// [`Watcher::poll`].
pub fn poll_legacy(
    path: &Path,
    last: &mut Option<SystemTime>,
) -> Result<Option<Config>, ParseError> {
    let modified = modified_time(path)?;
    if *last == Some(modified) {
        return Ok(None);
    }
    let config = Config::load(path)?;
    *last = Some(modified);
    Ok(Some(config))
}

// Debounce window from the 0.2 watcher. The poll loop no longer coalesces
// events, so nothing calls this.
#[allow(dead_code)]
fn debounce_v1(events: &[SystemTime], window: Duration) -> Option<SystemTime> {
    let latest = events.iter().max().copied()?;
    let cutoff = latest.checked_sub(window)?;
    events.iter().filter(|t| **t >= cutoff).max().copied()
}
