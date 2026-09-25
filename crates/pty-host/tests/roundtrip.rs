//! Echte PTYs gegen den In-Process-Host: öffnen, trennen, wieder anhängen mit
//! lückenlosem Replay, beenden. Windows: ConPTY liefert im cargo-test-Harness
//! keine Ausgabe (siehe apps/desktop terminal.rs) — dort nur der Vertragstest.

#![cfg(unix)]

use std::sync::mpsc::channel;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde_json::json;
use speccify_pty_host::{Client, DEFAULT_BUFFER_BYTES, Event, spawn_in_process};

fn connect(port: u16) -> (Client, std::sync::mpsc::Receiver<Event>) {
    let (sender, receiver) = channel();
    let client = Client::connect(
        port,
        "t",
        Box::new(move |event| {
            let _ = sender.send(event);
        }),
    )
    .unwrap();
    (client, receiver)
}

fn ticks(text: &str) -> Vec<u32> {
    text.lines()
        .filter_map(|line| line.trim().strip_prefix("tick "))
        .filter_map(|n| n.trim().parse().ok())
        .collect()
}

fn collect(
    receiver: &std::sync::mpsc::Receiver<Event>,
    id: &str,
    until: impl Fn(&str) -> bool,
    timeout: Duration,
) -> String {
    let mut text = String::new();
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        match receiver.recv_timeout(Duration::from_millis(200)) {
            Ok(Event::Out { id: got, data }) if got == id => {
                text.push_str(&String::from_utf8_lossy(&data));
                if until(&text) {
                    break;
                }
            }
            Ok(_) => {}
            Err(_) => {}
        }
    }
    text
}

#[test]
fn detach_and_reattach_replays_without_gap() {
    let (port, host) = spawn_in_process("t", DEFAULT_BUFFER_BYTES).unwrap();
    let (first, events) = connect(port);
    let script = "i=0; while [ $i -lt 400 ]; do echo tick $i; i=$((i+1)); sleep 0.02; done";
    first
        .open(
            "s1",
            "/bin/sh",
            &["-c".into(), script.into()],
            "/tmp",
            &[],
            80,
            24,
            b"",
            json!({"window": "project-x"}),
        )
        .unwrap();
    let before = collect(
        &events,
        "s1",
        |t| ticks(t).len() >= 10,
        Duration::from_secs(5),
    );
    assert!(
        ticks(&before).len() >= 10,
        "live output arrives: {before:?}"
    );
    assert_eq!(host.live_sessions(), 1);
    drop(first); // App-Ende: nur trennen
    std::thread::sleep(Duration::from_millis(300));
    assert_eq!(host.live_sessions(), 1, "session survives the client");

    let (second, events) = connect(port);
    let listed = second.list().unwrap();
    assert_eq!(listed.len(), 1);
    assert_eq!(listed[0]["meta"]["window"], "project-x");
    assert_eq!(listed[0]["exited"], false);
    let reply = second.attach("s1").unwrap();
    let replay = String::from_utf8_lossy(&reply.replay).to_string();
    let replayed = ticks(&replay);
    assert_eq!(replayed.first(), Some(&0), "replay starts at the beginning");
    assert!(replayed.len() > 10);
    let live = collect(
        &events,
        "s1",
        |t| ticks(t).len() >= 5,
        Duration::from_secs(5),
    );
    let mut all = replay.clone();
    all.push_str(&live);
    let sequence = ticks(&all);
    for pair in sequence.windows(2) {
        assert_eq!(
            pair[1],
            pair[0] + 1,
            "no gap or duplicate between replay and live: {sequence:?}"
        );
    }
    second.write("s1", b"").unwrap();
    second.resize("s1", 100, 30).unwrap();
    assert!(second.kill("s1").unwrap());
    assert!(!second.kill("s1").unwrap());
    std::thread::sleep(Duration::from_millis(300));
    assert_eq!(host.live_sessions(), 0);
    assert!(second.list().unwrap().is_empty());
}

#[test]
fn exit_is_reported_and_retained_for_late_attach() {
    let (port, host) = spawn_in_process("t", DEFAULT_BUFFER_BYTES).unwrap();
    let (client, events) = connect(port);
    client
        .open(
            "s2",
            "/bin/sh",
            &["-c".into(), "echo fertig; exit 3".into()],
            "/tmp",
            &[],
            80,
            24,
            b"",
            json!(null),
        )
        .unwrap();
    let mut exit = None;
    let deadline = Instant::now() + Duration::from_secs(5);
    while Instant::now() < deadline {
        if let Ok(Event::Exit { id, code }) = events.recv_timeout(Duration::from_millis(200)) {
            if id == "s2" {
                exit = code;
                break;
            }
        }
    }
    assert_eq!(exit, Some(3));
    assert_eq!(host.live_sessions(), 0);
    let listed = client.list().unwrap();
    assert_eq!(listed[0]["exited"], true);
    let reply = client.attach("s2").unwrap();
    assert!(String::from_utf8_lossy(&reply.replay).contains("fertig"));
    assert_eq!(reply.exit_code, Some(3));
}

#[test]
fn input_reaches_the_session_and_buffer_is_bounded() {
    let (port, _host) = spawn_in_process("t", 64 * 1024).unwrap();
    let (client, events) = connect(port);
    client
        .open(
            "s3",
            "/bin/sh",
            &["-c".into(), "cat".into()],
            "/tmp",
            &[("SPECCIFY_TEST".into(), "1".into())],
            80,
            24,
            b"hallo pty\n",
            json!(null),
        )
        .unwrap();
    let echoed = collect(
        &events,
        "s3",
        |t| t.contains("hallo pty"),
        Duration::from_secs(5),
    );
    assert!(
        echoed.contains("hallo pty"),
        "initial input is written before the first read: {echoed:?}"
    );
    let big = vec![b'x'; 200 * 1024];
    client.write("s3", &big).unwrap();
    client.write("s3", b"\n").unwrap();
    let seen = Arc::new(Mutex::new(0usize));
    let deadline = Instant::now() + Duration::from_secs(5);
    while Instant::now() < deadline {
        if let Ok(Event::Out { data, .. }) = events.recv_timeout(Duration::from_millis(200)) {
            *seen.lock().unwrap() += data.len();
            if *seen.lock().unwrap() >= 200 * 1024 {
                break;
            }
        }
    }
    let listed = client.list().unwrap();
    assert!(
        listed[0]["buffered"].as_u64().unwrap() <= 64 * 1024,
        "ring buffer keeps the limit: {}",
        listed[0]["buffered"]
    );
    client.kill("s3").unwrap();
}
