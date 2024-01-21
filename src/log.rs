use std::collections::HashMap;
use std::fs::write;
use serde::{Deserialize, Serialize};
use crate::file_change_log::FileChangeLog;

#[derive(Serialize, Deserialize)]
pub struct CommitLog {
	message: String,
	old_files: Vec<String>,
	new_files: Vec<String>,
	changes: HashMap<String, FileChangeLog>,
}

#[derive(Serialize, Deserialize)]
pub struct Log {
	head: String,
	timeline: Vec<String>,
	commits: HashMap<String, CommitLog>,
}

impl Log {
	fn new() -> Self {
		Log{head: "".to_string(), timeline: vec![], commits: HashMap::new()}
	}
}

pub fn init_log_file(path: String) {
	write(path, serde_json::to_string(&Log::new()).unwrap())
		.expect("error: cannot initialize log file");
}
