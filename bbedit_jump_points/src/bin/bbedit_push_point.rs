//! Get the front BBEdit window's current location, and store it.

use std::env;
use bbedit_jump_points::*;
use chrono::{Duration, Utc};

fn main() {
    let bbedit_pid = pid_for_asn(front_app_asn());

    let max_age = Duration::hours(1);

    let points_pathbuf = get_points_pathbuf();
    let points_path = points_pathbuf.as_path();

    let now = Utc::now();
    let mut points_data = get_points(points_path, now - max_age);

    let new_point = JumpPoint {
        filename: env::var("BB_DOC_PATH").unwrap(),
        line: env::var("BB_DOC_SELSTART_LINE")
            .unwrap()
            .parse::<i64>()
            .unwrap(),
        column: env::var("BB_DOC_SELSTART_COLUMN")
            .unwrap()
            .parse::<i64>()
            .unwrap(),
        added: now,
    };

    if let Some(points) = points_data.get_mut(&bbedit_pid) {
        points.push(new_point);
    } else {
        points_data.insert(bbedit_pid, vec![new_point]);
    }
    save_points(points_path, points_data);
}
