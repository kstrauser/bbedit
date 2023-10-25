//! Tools for saving and restoring a stack of points in BBEdit docs.
//!
//! BBEdit doesn't remember where you were before calling various "Go to..." commands. These
//! external programs save its state to a YAML file in the user's data directory, and restore
//! it afterward.

#![warn(missing_docs)]

use chrono::{DateTime, Utc};
use directories::ProjectDirs;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{create_dir, read, write};
use std::path::{Path, PathBuf};
use std::process::Command;

/// Represent a cursor location in BBEdit.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub struct JumpPoint {
    /// The full path to a file.
    pub filename: String,
    /// The line number (1-indexed) where the cursor was. It's at least
    /// _possible_ that, say, a log file might have more than 4B lines.
    /// RAM's cheap. Store this in a 64-bit value just in case.
    pub line: i64,
    /// The column number (1-indexed) where the cursor was, also as a
    /// 64-bit int for the same reasons as `line`.
    pub column: i64,
    /// The UTC timestamp when this point was recorded.
    pub added: DateTime<Utc>,
}

/// BBEdit may have multiple windows open at once, each with its own
/// pid. They shouldn't interfere with each other: If you're writing
/// Python in 1 window, you don't want to get popped back into some Rust
/// code in another. The points map's key is an int process ID, and its
/// value is a vector of JumpPoints.
pub type PointsMap = HashMap<i32, Vec<JumpPoint>>;

/// Return the path to the `points.yaml` file storing the `PointsMap` data.
///
/// This also ensures that the project directory where the file is
/// stored exists.
pub fn get_points_pathbuf() -> PathBuf {
    let project_dirs = ProjectDirs::from("net", "honeypot", "bbedit_jump_points").unwrap();
    let data_dir = project_dirs.data_dir();
    let _ = create_dir(data_dir);
    data_dir.join("points.yaml")
}

/// Return the ASN of the frontmost open window.
pub fn front_app_asn() -> String {
    let visible_process_list_out = String::from_utf8(
        Command::new("lsappinfo")
            .arg("visibleProcessList")
            .output()
            .unwrap()
            .stdout,
    )
    .unwrap();

    visible_process_list_out
        .split(' ')
        .next()
        .unwrap()
        .to_string()
}

/// Return the pid of the given ASN.
pub fn pid_for_asn(asn: String) -> i32 {
    // I'm gonna vent here for a second. If you get this command line
    // wrong, bummer. `lsappinfo` will still exit with status code 0,
    // and will write some text to stdout that looks like an error
    // message to a human, but comprises an undocumented list of
    // possible strings. It does nothing to help you detect that
    // something went badly.
    let info_out = String::from_utf8(
        Command::new("lsappinfo")
            .args(["info", "-only", "pid", &asn])
            .output()
            .unwrap()
            .stdout,
    )
    .unwrap();
    for line in info_out.split('\n') {
        if line.starts_with("\"pid\"=") {
            let pid = line.split('=').nth(1).unwrap();
            return pid.parse::<i32>().unwrap();
        }
    }

    panic!("Couldn't get the pid for ASN \"{}\"", asn);
}

/// Return the previously stored PointsMap.
pub fn get_points(points_path: &Path, oldest_time: DateTime<Utc>) -> PointsMap {
    // Get the points file's contents, or an empty string if we can't.
    let points_data = String::from_utf8(match read(points_path) {
        Ok(data) => data,
        Err(_) => vec![],
    })
    .unwrap();

    points_from(points_data, oldest_time)
}

/// Parse a string into a PointsMap object of unexpired points.
///
/// This removes all expired points from each pid's vec of points, and
/// then removes any pids that no longer non-expired points. In other
/// words, if you wait long enough between calls, this will eventually
/// return an empty mapping.
fn points_from(points_data: String, oldest_time: DateTime<Utc>) -> PointsMap {
    let mut points_map: PointsMap = serde_yaml::from_str(&points_data).unwrap();

    // Get rid of expired points.
    for points in points_map.values_mut() {
        points.retain(|point| point.added >= oldest_time);
    }
    // Get rid of point vecs that are empty after pruning.
    points_map.retain(|_, points| !points.is_empty());

    points_map
}

/// Store the PointsMap to the points file.
pub fn save_points(points_path: &Path, points_map: PointsMap) {
    // Get rid of empty point vecs.
    let mut points_map = points_map.clone();
    points_map.retain(|_, points| !points.is_empty());
    let points_data = serde_yaml::to_string(&points_map).unwrap();
    let _ = write(points_path, points_data);
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::prelude::*;

    const SAVED_POINTS: &str = "\
123:
- filename: /tmp/foo
  line: 9
  column: 42
  added: 2023-10-03T07:59:59Z
- filename: /tmp/bar
  line: 17
  column: 23
  added: 2023-10-03T08:00:00Z
    ";

    #[test]
    fn all_points_are_current() {
        let expiration = Utc.with_ymd_and_hms(2023, 10, 3, 7, 59, 59).unwrap();

        let points_map = points_from(SAVED_POINTS.to_string(), expiration);

        assert!(points_map.eq(&HashMap::from([(
            123,
            vec![
                JumpPoint {
                    filename: "/tmp/foo".to_string(),
                    line: 9,
                    column: 42,
                    added: Utc.with_ymd_and_hms(2023, 10, 3, 7, 59, 59).unwrap()
                },
                JumpPoint {
                    filename: "/tmp/bar".to_string(),
                    line: 17,
                    column: 23,
                    added: Utc.with_ymd_and_hms(2023, 10, 3, 8, 0, 0).unwrap()
                },
            ]
        )])));
    }

    #[test]
    fn some_points_are_current() {
        let expiration = Utc.with_ymd_and_hms(2023, 10, 3, 8, 0, 0).unwrap();

        let points_map = points_from(SAVED_POINTS.to_string(), expiration);

        assert!(points_map.eq(&HashMap::from([(
            123,
            vec![JumpPoint {
                filename: "/tmp/bar".to_string(),
                line: 17,
                column: 23,
                added: Utc.with_ymd_and_hms(2023, 10, 3, 8, 0, 0).unwrap()
            },]
        )])));
    }

    #[test]
    fn no_points_are_current() {
        let expiration = Utc.with_ymd_and_hms(2023, 10, 3, 8, 0, 1).unwrap();

        let points_map = points_from(SAVED_POINTS.to_string(), expiration);

        assert!(points_map.eq(&HashMap::new()));
    }
}
