//! Local HTTP boundary, shared by RPC, health/banner and Exec SSE requests.
//! Native clients omit Origin. No browser origins are currently authorized.

use tiny_http::{Header, Method, Request};

pub const MAX_HTTP_BODY_BYTES: usize = 1024 * 1024;

pub(crate) struct Rejection {
    pub status: u16,
    pub code: &'static str,
    pub message: &'static str,
}

fn reject(status: u16, code: &'static str, message: &'static str) -> Rejection {
    Rejection {
        status,
        code,
        message,
    }
}

fn values<'a>(headers: &'a [Header], name: &'static str) -> Vec<&'a str> {
    headers
        .iter()
        .filter(|h| h.field.equiv(name))
        .map(|h| h.value.as_str())
        .collect()
}

pub(crate) fn validate(request: &Request, port: u16) -> Result<(), Rejection> {
    let headers = request.headers();
    let hosts = values(headers, "Host");
    let valid_host = hosts.len() == 1
        && ["127.0.0.1", "localhost"].iter().any(|host| {
            hosts[0].eq_ignore_ascii_case(&format!("{host}:{port}"))
                || (port == 80 && hosts[0].eq_ignore_ascii_case(host))
        });
    if !valid_host {
        return Err(reject(
            403,
            "invalid_host",
            "Host must identify this loopback server and port.",
        ));
    }
    // Reject even empty, opaque/null, duplicate and local origins. In particular,
    // another service on localhost does not implicitly gain tool access.
    if !values(headers, "Origin").is_empty() {
        return Err(reject(
            403,
            "origin_not_allowed",
            "Browser origins are not authorized for this local MCP server.",
        ));
    }
    if request.method() != &Method::Get && request.method() != &Method::Post {
        return Err(reject(
            405,
            "method_not_allowed",
            "Use GET for the banner or POST for JSON requests.",
        ));
    }

    let lengths = values(headers, "Content-Length");
    let encodings = values(headers, "Transfer-Encoding");
    if lengths.len() > 1
        || encodings.len() > 1
        || (!lengths.is_empty() && !encodings.is_empty())
        || lengths.first().is_some_and(|v| {
            v.is_empty() || !v.bytes().all(|b| b.is_ascii_digit()) || v.parse::<usize>().is_err()
        })
        || encodings
            .first()
            .is_some_and(|v| !v.eq_ignore_ascii_case("chunked"))
    {
        return Err(reject(
            400,
            "invalid_framing",
            "Ambiguous or unsupported request framing.",
        ));
    }
    if request
        .body_length()
        .is_some_and(|length| length > MAX_HTTP_BODY_BYTES)
    {
        return Err(reject(
            413,
            "body_too_large",
            "Request body exceeds the 1 MiB limit.",
        ));
    }
    if request.method() == &Method::Post {
        let types = values(headers, "Content-Type");
        if types.len() != 1
            || !types[0]
                .split(';')
                .next()
                .unwrap_or("")
                .trim()
                .eq_ignore_ascii_case("application/json")
        {
            return Err(reject(
                415,
                "unsupported_media_type",
                "POST requires Content-Type: application/json.",
            ));
        }
    }
    Ok(())
}
