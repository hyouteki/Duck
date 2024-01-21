use std::collections::HashMap;
use core::cmp::max;
use serde::{Deserialize, Serialize};

pub struct FileDiffLog {
	pub add: HashMap<i32, String>,
	pub com: Vec<String>,
	pub del: HashMap<i32, String>,
}

impl FileDiffLog {
	fn new(
		add: HashMap<i32, String>,
		com: Vec<String>,
		del: HashMap<i32, String>
	) -> Self {FileDiffLog{add: add, com: com, del: del}}
}

#[derive(Serialize, Deserialize)]
pub struct FileChangeLog {
	pub add: HashMap<i32, String>,
	pub del: HashMap<i32, String>,
}

impl FileChangeLog {
	fn from_diff(diff: FileDiffLog) -> Self {
		FileChangeLog{add: diff.add, del: diff.del}
	}
}


pub fn get_file_diff_log(
	old_file_lines: Vec<String>,
	new_file_lines: Vec<String>
) -> FileDiffLog {
	let (old_len, new_len) = (old_file_lines.len(), new_file_lines.len());

	// finding longest common subsequence
	let mut dp = vec![vec![0; new_len+1]; old_len];
	for i in 1..old_len+1 {
		for j in 1..new_len+1 {
			dp[i][j] = if old_file_lines[i-1] == new_file_lines[j-1]
			{1+dp[i-1][j-1]} else {max(dp[i-1][j], dp[i][j-1])};
		}
 	}

	// finding common lines between both versions of the file
	let mut com = vec!["".to_string(); dp[old_len][new_len]];
	let (mut old_ptr, mut com_ptr, mut new_ptr) = (
		old_len, dp[old_len][new_len]-1, new_len);
	while old_ptr > 0 && new_ptr > 0 {
		if old_file_lines[old_ptr-1] == new_file_lines[new_ptr-1] {
			com[com_ptr] = old_file_lines[old_ptr-1].to_string();
			old_ptr -= 1;
			com_ptr -= 1;
			new_ptr -= 1;
		} else if dp[old_ptr-1][new_ptr] > dp[old_ptr][new_ptr-1] {
			old_ptr -= 1;
		} else {new_ptr -= 1;}
	}

	// newly added lines
	let mut add: HashMap<i32, String> = HashMap::new();
	com_ptr = 0;
	for i in 0..new_len {
		if com_ptr < com.len() && new_file_lines[i] == com[com_ptr] {
			com_ptr += 1;
		} else {
			add.insert(i as i32, new_file_lines[i].to_string());
		}
	}
	
	// deleted lines
	let mut del: HashMap<i32, String> = HashMap::new();
	com_ptr = 0;
	for i in 0..old_len {
		if com_ptr < com.len() && old_file_lines[i] == com[com_ptr] {
			com_ptr += 1;
		} else {
			del.insert(i as i32, old_file_lines[i].to_string());
		}
	}
	
	FileDiffLog::new(add, com, del)
}

pub fn get_file_change_log(
	old_file_lines: Vec<String>,
	new_file_lines: Vec<String>
) -> FileChangeLog {
	FileChangeLog::from_diff(get_file_diff_log(old_file_lines, new_file_lines))
}
