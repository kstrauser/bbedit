//! Load the front BBEdit window's previous jump point, and return to it.

use bbedit_jump_points::*;
use chrono::{Duration, Utc};
pub(crate) use std::process::Command;

fn main() {
    let bbedit_pid = pid_for_asn(front_app_asn());

    let max_age = Duration::hours(1);

    let points_pathbuf = get_points_pathbuf();
    let points_path = points_pathbuf.as_path();

    let now = Utc::now();
    let mut points_data = get_points(points_path, now - max_age);

    if let Some(points) = points_data.get_mut(&bbedit_pid) {
        let last_point = points.pop().unwrap();
        save_points(points_path, points_data);

        let _ = Command::new("/usr/local/bin/bbedit")
            .arg(format!("+{}:{}", &last_point.line, &last_point.column))
            .arg(&last_point.filename)
            .output();

        eprintln!("popped: {} => {:?}", bbedit_pid, last_point);
    } else {
        eprintln!("no more return points for pid {}", bbedit_pid);
    }
}
