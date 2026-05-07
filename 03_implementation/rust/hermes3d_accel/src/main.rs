use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::env;
use std::error::Error;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};

type AccelResult<T> = Result<T, Box<dyn Error>>;

fn main() {
    if let Err(err) = run() {
        eprintln!("{err}");
        std::process::exit(2);
    }
}

fn run() -> AccelResult<()> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 {
        return Err("usage: hermes3d-accel <sha256|gcode-meta|stl-meta> <path>".into());
    }
    let path = PathBuf::from(&args[2]);
    let payload = match args[1].as_str() {
        "sha256" => command_sha256(&path)?,
        "gcode-meta" => command_gcode_meta(&path)?,
        "stl-meta" => command_stl_meta(&path)?,
        other => return Err(format!("unknown command: {other}").into()),
    };
    println!("{}", serde_json::to_string(&payload)?);
    Ok(())
}

fn command_sha256(path: &Path) -> AccelResult<Value> {
    let (size_bytes, digest) = sha256_file(path)?;
    Ok(json!({
        "kind": "sha256",
        "path": path.to_string_lossy(),
        "size_bytes": size_bytes,
        "sha256": digest,
        "source": "rust"
    }))
}

fn command_gcode_meta(path: &Path) -> AccelResult<Value> {
    let (size_bytes, digest) = sha256_file(path)?;
    let text = read_bounded_text(path, 65_536, 65_536)?;
    let mut estimated_minutes: Option<f64> = None;
    let mut estimated_filament_mm: Option<f64> = None;
    let mut estimated_filament_g: Option<f64> = None;
    let mut layer_count: Option<u64> = None;

    for line in text.lines() {
        let clean = line.trim().trim_start_matches(';').trim();
        let lower = clean.to_ascii_lowercase();

        if estimated_minutes.is_none()
            && (lower.starts_with("estimated printing time")
                || lower.starts_with("total estimated time"))
        {
            if let Some(raw) = after_separator(clean) {
                estimated_minutes = parse_minutes(raw);
            }
        }

        if estimated_filament_mm.is_none() && lower.starts_with("filament used [mm]") {
            estimated_filament_mm = after_separator(clean).and_then(parse_first_float);
        }

        if estimated_filament_g.is_none() && lower.starts_with("filament used [g]") {
            estimated_filament_g = after_separator(clean).and_then(parse_first_float);
        }

        if layer_count.is_none()
            && (lower.starts_with("total layer number")
                || lower.starts_with("num layers")
                || lower.starts_with("total layer count"))
        {
            layer_count = after_separator(clean)
                .and_then(|raw| raw.split_whitespace().next())
                .and_then(|raw| raw.parse::<u64>().ok());
        }
    }

    Ok(json!({
        "kind": "gcode_metadata",
        "path": path.to_string_lossy(),
        "size_bytes": size_bytes,
        "sha256": digest,
        "estimated_minutes": estimated_minutes,
        "estimated_filament_mm": estimated_filament_mm,
        "estimated_filament_g": estimated_filament_g,
        "layer_count": layer_count,
        "source": "rust"
    }))
}

fn command_stl_meta(path: &Path) -> AccelResult<Value> {
    let (size_bytes, digest) = sha256_file(path)?;
    let mut file = File::open(path)?;
    if size_bytes < 84 {
        return Ok(json!({
            "kind": "stl_metadata",
            "path": path.to_string_lossy(),
            "size_bytes": size_bytes,
            "sha256": digest,
            "format": "unsupported_or_malformed",
            "reason": "file is too small for binary STL",
            "source": "rust"
        }));
    }

    let mut header = [0_u8; 80];
    file.read_exact(&mut header)?;
    let mut count_buf = [0_u8; 4];
    file.read_exact(&mut count_buf)?;
    let triangle_count = u32::from_le_bytes(count_buf) as u64;
    let expected_size = 84_u64.saturating_add(triangle_count.saturating_mul(50));
    if expected_size != size_bytes {
        return Ok(json!({
            "kind": "stl_metadata",
            "path": path.to_string_lossy(),
            "size_bytes": size_bytes,
            "sha256": digest,
            "format": "unsupported_or_malformed",
            "reason": "file size does not match binary STL triangle count",
            "source": "rust"
        }));
    }

    let mut min = [f32::INFINITY; 3];
    let mut max = [f32::NEG_INFINITY; 3];
    let mut record = [0_u8; 50];
    for _ in 0..triangle_count {
        file.read_exact(&mut record)?;
        for vertex in 0..3 {
            let base = 12 + vertex * 12;
            let xyz = [
                f32::from_le_bytes(record[base..base + 4].try_into()?),
                f32::from_le_bytes(record[base + 4..base + 8].try_into()?),
                f32::from_le_bytes(record[base + 8..base + 12].try_into()?),
            ];
            for axis in 0..3 {
                min[axis] = min[axis].min(xyz[axis]);
                max[axis] = max[axis].max(xyz[axis]);
            }
        }
    }

    let (bbox_mm, extents_mm) = if triangle_count == 0 {
        (Value::Null, Value::Null)
    } else {
        (
            json!([
                [min[0] as f64, min[1] as f64, min[2] as f64],
                [max[0] as f64, max[1] as f64, max[2] as f64]
            ]),
            json!([
                (max[0] - min[0]) as f64,
                (max[1] - min[1]) as f64,
                (max[2] - min[2]) as f64
            ]),
        )
    };

    Ok(json!({
        "kind": "stl_metadata",
        "path": path.to_string_lossy(),
        "size_bytes": size_bytes,
        "sha256": digest,
        "format": "binary_stl",
        "triangle_count": triangle_count,
        "bbox_mm": bbox_mm,
        "extents_mm": extents_mm,
        "source": "rust"
    }))
}

fn sha256_file(path: &Path) -> AccelResult<(u64, String)> {
    let mut file = File::open(path)?;
    let size_bytes = file.metadata()?.len();
    let mut hasher = Sha256::new();
    let mut buffer = vec![0_u8; 1 << 20];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }
    let digest = hasher.finalize();
    Ok((size_bytes, hex_lower(&digest)))
}

fn read_bounded_text(path: &Path, head_bytes: u64, tail_bytes: u64) -> AccelResult<String> {
    let mut file = File::open(path)?;
    let size = file.metadata()?.len();
    let mut out = Vec::new();
    let head_len = head_bytes.min(size) as usize;
    let mut head = vec![0_u8; head_len];
    file.read_exact(&mut head)?;
    out.extend_from_slice(&head);

    if size > head_bytes + tail_bytes {
        file.seek(SeekFrom::End(-(tail_bytes as i64)))?;
        let mut tail = Vec::new();
        file.read_to_end(&mut tail)?;
        out.push(b'\n');
        out.extend_from_slice(&tail);
    }
    Ok(String::from_utf8_lossy(&out).to_string())
}

fn after_separator(text: &str) -> Option<&str> {
    text.split_once('=')
        .or_else(|| text.split_once(':'))
        .map(|(_, right)| right.trim())
}

fn parse_first_float(text: &str) -> Option<f64> {
    text.split_whitespace()
        .next()
        .unwrap_or(text)
        .trim()
        .parse::<f64>()
        .ok()
}

fn parse_minutes(text: &str) -> Option<f64> {
    let clean = text.trim();
    let colon_parts: Vec<&str> = clean.split(':').collect();
    if colon_parts.len() == 2 || colon_parts.len() == 3 {
        let parsed: Option<Vec<u64>> = colon_parts
            .iter()
            .map(|part| part.trim().parse::<u64>().ok())
            .collect();
        if let Some(values) = parsed {
            return if values.len() == 3 {
                Some(values[0] as f64 * 60.0 + values[1] as f64 + values[2] as f64 / 60.0)
            } else {
                Some(values[0] as f64 + values[1] as f64 / 60.0)
            };
        }
    }

    let mut days = 0_u64;
    let mut hours = 0_u64;
    let mut minutes = 0_u64;
    let mut seconds = 0_u64;
    let mut seen = false;
    for raw in clean.split_whitespace() {
        let token = raw.trim().to_ascii_lowercase();
        if let Some(value) = token.strip_suffix('d').and_then(|n| n.parse::<u64>().ok()) {
            days = value;
            seen = true;
        } else if let Some(value) = token.strip_suffix('h').and_then(|n| n.parse::<u64>().ok()) {
            hours = value;
            seen = true;
        } else if let Some(value) = token.strip_suffix('m').and_then(|n| n.parse::<u64>().ok()) {
            minutes = value;
            seen = true;
        } else if let Some(value) = token.strip_suffix('s').and_then(|n| n.parse::<u64>().ok()) {
            seconds = value;
            seen = true;
        }
    }
    if seen {
        Some(days as f64 * 1440.0 + hours as f64 * 60.0 + minutes as f64 + seconds as f64 / 60.0)
    } else {
        None
    }
}

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::io::Write;

    fn temp_file(name: &str) -> PathBuf {
        let mut path = env::temp_dir();
        path.push(format!(
            "hermes3d_accel_{}_{}_{}",
            std::process::id(),
            chrono_free_nonce(),
            name
        ));
        path
    }

    fn chrono_free_nonce() -> u128 {
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    }

    #[test]
    fn parses_gcode_metadata() {
        let path = temp_file("meta.gcode");
        fs::write(
            &path,
            "; total layer count = 87\n; filament used [mm] = 4523.42\n; filament used [g] = 13.6\n; estimated printing time (normal mode) = 1h 23m 15s\n",
        )
        .unwrap();
        let meta = command_gcode_meta(&path).unwrap();
        assert_eq!(meta["layer_count"].as_u64(), Some(87));
        assert_eq!(meta["estimated_filament_mm"].as_f64(), Some(4523.42));
        assert_eq!(meta["estimated_filament_g"].as_f64(), Some(13.6));
        assert!((meta["estimated_minutes"].as_f64().unwrap() - 83.25).abs() < 0.01);
        let _ = fs::remove_file(path);
    }

    #[test]
    fn parses_binary_stl_bounds() {
        let path = temp_file("one_triangle.stl");
        let mut file = File::create(&path).unwrap();
        file.write_all(&[0_u8; 80]).unwrap();
        file.write_all(&(1_u32).to_le_bytes()).unwrap();
        file.write_all(&[0_u8; 12]).unwrap();
        for xyz in [[0.0_f32, 0.0, 0.0], [10.0, 0.0, 0.0], [0.0, 20.0, 3.0]] {
            for value in xyz {
                file.write_all(&value.to_le_bytes()).unwrap();
            }
        }
        file.write_all(&[0_u8; 2]).unwrap();
        drop(file);

        let meta = command_stl_meta(&path).unwrap();
        assert_eq!(meta["format"].as_str(), Some("binary_stl"));
        assert_eq!(meta["triangle_count"].as_u64(), Some(1));
        assert_eq!(meta["extents_mm"][0].as_f64(), Some(10.0));
        assert_eq!(meta["extents_mm"][1].as_f64(), Some(20.0));
        assert_eq!(meta["extents_mm"][2].as_f64(), Some(3.0));
        let _ = fs::remove_file(path);
    }

    #[test]
    fn parses_colon_time() {
        assert_eq!(parse_minutes("1:02:03").unwrap(), 62.05);
        assert_eq!(parse_minutes("02:30").unwrap(), 2.5);
    }
}
