//! A Rust implementation of the `python-dotenv==1.2.2` parser contract.
//!
//! The parser deliberately produces one `Binding` per upstream parser step.
//! Keeping the original source slice and starting line is required by the
//! `set_key` and `unset_key` APIs, which rewrite a file without normalizing
//! comments, malformed lines, or line endings.

use std::collections::HashMap;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Original {
    pub string: String,
    pub line: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Binding {
    pub key: Option<String>,
    pub value: Option<String>,
    pub original: Original,
    pub error: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum VariableAtom {
    Literal(String),
    Variable {
        name: String,
        default: Option<String>,
    },
}

#[derive(Clone, Copy, Debug)]
struct Position {
    chars: usize,
    line: usize,
}

impl Position {
    fn start() -> Self {
        Self { chars: 0, line: 1 }
    }
}

#[derive(Debug)]
struct ParseError;

/// Cursor equivalent to the upstream `Reader`.
struct Reader<'a> {
    source: &'a str,
    position: Position,
    mark: Position,
}

impl<'a> Reader<'a> {
    fn new(source: &'a str) -> Self {
        Self {
            source,
            position: Position::start(),
            mark: Position::start(),
        }
    }

    fn has_next(&self) -> bool {
        self.position.chars < self.source.len()
    }

    fn peek(&self) -> Option<char> {
        self.source[self.position.chars..].chars().next()
    }

    fn set_mark(&mut self) {
        self.mark = self.position;
    }

    fn get_marked(&self) -> Original {
        Original {
            string: self.source[self.mark.chars..self.position.chars].to_owned(),
            line: self.mark.line,
        }
    }

    /// Advance to a byte offset and count Python's `(_newline)` matches.
    /// `\r\n` counts as one newline, while separate reads of `\r` and `\n`
    /// count separately, matching the upstream regex reader.
    fn advance_to(&mut self, end: usize) {
        let slice = &self.source[self.position.chars..end];
        let mut previous_was_cr = false;
        let mut newlines = 0usize;
        for c in slice.chars() {
            match c {
                '\r' => {
                    newlines += 1;
                    previous_was_cr = true;
                }
                '\n' => {
                    if !previous_was_cr {
                        newlines += 1;
                    }
                    previous_was_cr = false;
                }
                _ => previous_was_cr = false,
            }
        }
        self.position.chars = end;
        self.position.line += newlines;
    }

    fn consume_multiline_whitespace(&mut self) {
        let mut end = self.position.chars;
        while let Some((c, next)) = next_char(self.source, end) {
            if !c.is_whitespace() {
                break;
            }
            end = next;
        }
        self.advance_to(end);
    }

    fn consume_horizontal_whitespace_at(&self, mut index: usize) -> usize {
        while let Some((c, next)) = next_char(self.source, index) {
            if !is_horizontal_whitespace(c) {
                break;
            }
            index = next;
        }
        index
    }

    fn consume_export(&mut self) {
        let start = self.position.chars;
        if !self.source[start..].starts_with("export") {
            return;
        }
        let after = start + "export".len();
        let whitespace_end = self.consume_horizontal_whitespace_at(after);
        if whitespace_end > after {
            self.advance_to(whitespace_end);
        }
    }

    fn parse_key(&mut self) -> Result<Option<String>, ParseError> {
        match self.peek() {
            Some('#') => Ok(None),
            Some('\'') => self.parse_single_quoted_key().map(Some),
            Some(_) => {
                let start = self.position.chars;
                let mut end = start;
                while let Some((c, next)) = next_char(self.source, end) {
                    if c == '=' || c == '#' || c.is_whitespace() {
                        break;
                    }
                    end = next;
                }
                if end == start {
                    return Err(ParseError);
                }
                self.advance_to(end);
                Ok(Some(self.source[start..end].to_owned()))
            }
            None => Err(ParseError),
        }
    }

    fn parse_single_quoted_key(&mut self) -> Result<String, ParseError> {
        let start = self.position.chars;
        let (_, mut index) = next_char(self.source, start).ok_or(ParseError)?;
        let content_start = index;
        let mut content_end = None;
        while let Some((c, next)) = next_char(self.source, index) {
            if c == '\'' {
                content_end = Some(index);
                index = next;
                break;
            }
            index = next;
        }
        let Some(end_content) = content_end else {
            return Err(ParseError);
        };
        if end_content == content_start {
            return Err(ParseError);
        }
        let key = self.source[content_start..end_content].to_owned();
        self.advance_to(index);
        Ok(key)
    }

    fn parse_value(&mut self) -> Result<String, ParseError> {
        match self.peek() {
            Some('\'') => self.parse_quoted_value('\''),
            Some('"') => self.parse_quoted_value('"'),
            Some('\n') | Some('\r') | None => Ok(String::new()),
            Some(_) => self.parse_unquoted_value(),
        }
    }

    fn parse_quoted_value(&mut self, quote: char) -> Result<String, ParseError> {
        let start = self.position.chars;
        let (_, mut index) = next_char(self.source, start).ok_or(ParseError)?;
        let content_start = index;
        let mut content_end = None;
        while let Some((c, next)) = next_char(self.source, index) {
            if c == '\\' {
                // The upstream regex treats an escaped matching quote as a
                // pair; all other backslashes are ordinary input characters.
                if let Some((next_char_value, after_next)) = next_char(self.source, next) {
                    if next_char_value == quote {
                        index = after_next;
                        continue;
                    }
                }
                index = next;
                continue;
            }
            if c == quote {
                content_end = Some(index);
                index = next;
                break;
            }
            index = next;
        }
        let Some(end_content) = content_end else {
            // Do not advance on a failed regex match.  The caller must be able
            // to consume only `_rest_of_line` and recover at the next line.
            return Err(ParseError);
        };
        let raw = &self.source[content_start..end_content];
        let value = decode_quoted(raw, quote);
        self.advance_to(index);
        Ok(value)
    }

    fn parse_unquoted_value(&mut self) -> Result<String, ParseError> {
        let start = self.position.chars;
        let mut end = start;
        while let Some((c, next)) = next_char(self.source, end) {
            if c == '\r' || c == '\n' {
                break;
            }
            end = next;
        }
        let raw = &self.source[start..end];
        let value = parse_unquoted(raw);
        self.advance_to(end);
        Ok(value)
    }

    /// `_comment`: optional horizontal whitespace, `#`, and the rest of the
    /// physical line. If no `#` follows, this regex consumes nothing.
    fn consume_comment(&mut self) {
        let start = self.position.chars;
        let after_ws = self.consume_horizontal_whitespace_at(start);
        if self.source[after_ws..].starts_with('#') {
            let mut end = after_ws;
            while let Some((c, next)) = next_char(self.source, end) {
                if c == '\r' || c == '\n' {
                    break;
                }
                end = next;
            }
            self.advance_to(end);
        }
    }

    /// `_end_of_line`: horizontal whitespace followed by CRLF, LF, CR, or
    /// EOF. This operation is transactional when trailing non-whitespace text
    /// makes the match fail.
    fn consume_end_of_line(&mut self) -> Result<(), ParseError> {
        let start = self.position.chars;
        let after_ws = self.consume_horizontal_whitespace_at(start);
        let end = if after_ws == self.source.len() {
            after_ws
        } else if self.source[after_ws..].starts_with("\r\n") {
            after_ws + 2
        } else if matches!(self.source[after_ws..].chars().next(), Some('\r' | '\n')) {
            next_char(self.source, after_ws)
                .map(|(_, next)| next)
                .ok_or(ParseError)?
        } else {
            return Err(ParseError);
        };
        self.advance_to(end);
        Ok(())
    }

    /// `_rest_of_line` has the upstream alternation order `\r|\n|\r\n`.
    /// Consequently a CRLF on an error path consumes CR first and leaves LF
    /// for the next parse step, exactly as the Python regex reader does.
    fn consume_rest_of_line(&mut self) {
        let mut end = self.position.chars;
        while let Some((c, next)) = next_char(self.source, end) {
            if c == '\r' || c == '\n' {
                break;
            }
            end = next;
        }
        if let Some((c, next)) = next_char(self.source, end) {
            if c == '\r' || c == '\n' {
                end = next;
            }
        }
        self.advance_to(end);
    }
}

fn next_char(source: &str, index: usize) -> Option<(char, usize)> {
    source[index..]
        .chars()
        .next()
        .map(|c| (c, index + c.len_utf8()))
}

fn is_horizontal_whitespace(c: char) -> bool {
    c.is_whitespace() && c != '\r' && c != '\n'
}

fn parse_binding(reader: &mut Reader<'_>) -> Binding {
    reader.set_mark();
    let result = (|| {
        reader.consume_multiline_whitespace();
        if !reader.has_next() {
            return Ok(Binding {
                key: None,
                value: None,
                original: reader.get_marked(),
                error: false,
            });
        }
        reader.consume_export();
        let key = reader.parse_key()?;
        let after_key = reader.consume_horizontal_whitespace_at(reader.position.chars);
        reader.advance_to(after_key);
        let value = if reader.peek() == Some('=') {
            let (_, after_equal) =
                next_char(reader.source, reader.position.chars).ok_or(ParseError)?;
            let after_equal_ws = reader.consume_horizontal_whitespace_at(after_equal);
            reader.advance_to(after_equal_ws);
            Some(reader.parse_value()?)
        } else {
            None
        };
        reader.consume_comment();
        reader.consume_end_of_line()?;
        Ok(Binding {
            key,
            value,
            original: reader.get_marked(),
            error: false,
        })
    })();

    match result {
        Ok(binding) => binding,
        Err(ParseError) => {
            reader.consume_rest_of_line();
            Binding {
                key: None,
                value: None,
                original: reader.get_marked(),
                error: true,
            }
        }
    }
}

/// Parse source in the same binding boundaries and order as upstream
/// `parse_stream()`. Blank/comment bindings are retained for the facade to
/// filter, and invalid bindings are retained with `error=true`.
pub fn parse_bindings(text: &str) -> Vec<Binding> {
    let mut reader = Reader::new(text);
    let mut bindings = Vec::new();
    while reader.has_next() {
        bindings.push(parse_binding(&mut reader));
    }
    bindings
}

/// Parse bindings in source order and resolve references using the environment
/// plus values already seen in the file. A repeated key keeps its first
/// position (as `OrderedDict` does) and receives the last value.
pub fn parse_and_resolve(
    text: &str,
    interpolate: bool,
    environment: &HashMap<String, String>,
) -> Vec<(String, Option<String>)> {
    parse_and_resolve_with_options(text, interpolate, true, environment).0
}

/// Parse and resolve all bindings in one Rust call. The second return value
/// preserves invalid-binding warning order for the Python facade.
pub fn parse_and_resolve_with_options(
    text: &str,
    interpolate: bool,
    override_environment: bool,
    environment: &HashMap<String, String>,
) -> (Vec<(String, Option<String>)>, Vec<usize>) {
    let mut result: Vec<(String, Option<String>)> = Vec::new();
    let mut positions: HashMap<String, usize> = HashMap::new();
    let mut previous: HashMap<String, Option<String>> = HashMap::new();
    let mut invalid_lines = Vec::new();

    for binding in parse_bindings(text) {
        if binding.error {
            invalid_lines.push(binding.original.line);
        }
        let Some(key) = binding.key else {
            continue;
        };
        let value = binding.value.map(|value| {
            if interpolate {
                interpolate_value(&value, environment, &previous, override_environment)
            } else {
                value
            }
        });
        if let Some(&position) = positions.get(&key) {
            result[position].1 = value.clone();
        } else {
            positions.insert(key.clone(), result.len());
            result.push((key.clone(), value.clone()));
        }
        previous.insert(key, value);
    }
    (result, invalid_lines)
}

fn decode_quoted(raw: &str, quote: char) -> String {
    let mut out = String::with_capacity(raw.len());
    let mut chars = raw.chars();
    while let Some(c) = chars.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        let Some(next) = chars.next() else {
            out.push('\\');
            break;
        };
        let decoded = match next {
            '\\' => '\\',
            '\'' if quote == '\'' || quote == '"' => '\'',
            '"' if quote == '"' => '"',
            'n' if quote == '"' => '\n',
            'r' if quote == '"' => '\r',
            't' if quote == '"' => '\t',
            'b' if quote == '"' => '\x08',
            'f' if quote == '"' => '\x0c',
            'a' if quote == '"' => '\x07',
            'v' if quote == '"' => '\x0b',
            _ => {
                out.push('\\');
                next
            }
        };
        out.push(decoded);
    }
    out
}

fn parse_unquoted(raw: &str) -> String {
    let mut comment_start = None;
    let mut previous_was_whitespace = false;
    for (index, c) in raw.char_indices() {
        if c == '#' && previous_was_whitespace {
            let mut start = index;
            while start > 0 {
                let Some((prev_index, prev)) = raw[..start].char_indices().next_back() else {
                    break;
                };
                if !prev.is_whitespace() {
                    break;
                }
                start = prev_index;
            }
            comment_start = Some(start);
            break;
        }
        previous_was_whitespace = c.is_whitespace();
    }
    let end = comment_start.unwrap_or(raw.len());
    raw[..end].trim_end().to_owned()
}

/// Tokenize the exact POSIX variable grammar used by
/// `python-dotenv==1.2.2`. The implementation intentionally follows regex
/// `finditer` search behavior: if a `${...}` candidate is invalid, searching
/// resumes inside it so a later nested `${...}` candidate can still match.
pub fn parse_variables(value: &str) -> Vec<VariableAtom> {
    let mut atoms = Vec::new();
    let mut literal_start = 0usize;
    let mut search_start = 0usize;

    while search_start < value.len() {
        let Some(relative_start) = value[search_start..].find("${") else {
            break;
        };
        let start = search_start + relative_start;
        let Some(relative_close) = value[start + 2..].find('}') else {
            break;
        };
        let close = start + 2 + relative_close;
        let expression = &value[start + 2..close];
        let (name, default) = match expression.split_once(":-") {
            Some((name, default)) if !name.contains(':') => {
                (name.to_owned(), Some(default.to_owned()))
            }
            Some(_) => {
                search_start = start + 2;
                continue;
            }
            None if expression.contains(':') => {
                search_start = start + 2;
                continue;
            }
            None => (expression.to_owned(), None),
        };

        if start > literal_start {
            atoms.push(VariableAtom::Literal(
                value[literal_start..start].to_owned(),
            ));
        }
        atoms.push(VariableAtom::Variable { name, default });
        literal_start = close + 1;
        search_start = literal_start;
    }

    if literal_start < value.len() {
        atoms.push(VariableAtom::Literal(value[literal_start..].to_owned()));
    }
    atoms
}

fn lookup(
    name: &str,
    environment: &HashMap<String, String>,
    previous: &HashMap<String, Option<String>>,
    override_environment: bool,
) -> Option<Option<String>> {
    if override_environment {
        match previous.get(name) {
            Some(value) => Some(value.clone()),
            None => environment.get(name).cloned().map(Some),
        }
    } else {
        match environment.get(name) {
            Some(value) => Some(Some(value.clone())),
            None => previous.get(name).cloned(),
        }
    }
}

fn interpolate_value(
    value: &str,
    environment: &HashMap<String, String>,
    previous: &HashMap<String, Option<String>>,
    override_environment: bool,
) -> String {
    let mut out = String::with_capacity(value.len());
    for atom in parse_variables(value) {
        match atom {
            VariableAtom::Literal(literal) => out.push_str(&literal),
            VariableAtom::Variable { name, default } => {
                match lookup(&name, environment, previous, override_environment) {
                    Some(Some(found)) => out.push_str(&found),
                    Some(None) => {}
                    None => out.push_str(default.as_deref().unwrap_or("")),
                }
            }
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn binding(
        key: Option<&str>,
        value: Option<&str>,
        original: &str,
        line: usize,
        error: bool,
    ) -> Binding {
        Binding {
            key: key.map(str::to_owned),
            value: value.map(str::to_owned),
            original: Original {
                string: original.to_owned(),
                line,
            },
            error,
        }
    }

    #[test]
    fn upstream_parser_fixtures() {
        let fixtures: &[(&str, &[Binding])] = &[
            ("", &[]),
            ("a=b", &[binding(Some("a"), Some("b"), "a=b", 1, false)]),
            ("'a'=b", &[binding(Some("a"), Some("b"), "'a'=b", 1, false)]),
            ("[=b", &[binding(Some("["), Some("b"), "[=b", 1, false)]),
            (
                " a = b ",
                &[binding(Some("a"), Some("b"), " a = b ", 1, false)],
            ),
            (
                "export a=b",
                &[binding(Some("a"), Some("b"), "export a=b", 1, false)],
            ),
            (
                " export 'a'=b",
                &[binding(Some("a"), Some("b"), " export 'a'=b", 1, false)],
            ),
            ("# a=b", &[binding(None, None, "# a=b", 1, false)]),
            (
                "a=b#c",
                &[binding(Some("a"), Some("b#c"), "a=b#c", 1, false)],
            ),
            (
                "a=b #c",
                &[binding(Some("a"), Some("b"), "a=b #c", 1, false)],
            ),
            (
                "a=b\t#c",
                &[binding(Some("a"), Some("b"), "a=b\t#c", 1, false)],
            ),
            (
                "a=b c",
                &[binding(Some("a"), Some("b c"), "a=b c", 1, false)],
            ),
            (
                "a=b\tc",
                &[binding(Some("a"), Some("b\tc"), "a=b\tc", 1, false)],
            ),
            (
                "a=b  c",
                &[binding(Some("a"), Some("b  c"), "a=b  c", 1, false)],
            ),
            (
                "a=b\u{a0} c",
                &[binding(
                    Some("a"),
                    Some("b\u{a0} c"),
                    "a=b\u{a0} c",
                    1,
                    false,
                )],
            ),
            (
                "a=b c ",
                &[binding(Some("a"), Some("b c"), "a=b c ", 1, false)],
            ),
            (
                "a='b c '",
                &[binding(Some("a"), Some("b c "), "a='b c '", 1, false)],
            ),
            (
                "a=\"b c \"",
                &[binding(Some("a"), Some("b c "), "a=\"b c \"", 1, false)],
            ),
            (
                "export export_a=1",
                &[binding(
                    Some("export_a"),
                    Some("1"),
                    "export export_a=1",
                    1,
                    false,
                )],
            ),
            (
                "export port=8000",
                &[binding(
                    Some("port"),
                    Some("8000"),
                    "export port=8000",
                    1,
                    false,
                )],
            ),
            (
                "a=\"b\nc\"",
                &[binding(Some("a"), Some("b\nc"), "a=\"b\nc\"", 1, false)],
            ),
            (
                "a='b\nc'",
                &[binding(Some("a"), Some("b\nc"), "a='b\nc'", 1, false)],
            ),
            (
                "a=\"b\\nc\"",
                &[binding(Some("a"), Some("b\nc"), "a=\"b\\nc\"", 1, false)],
            ),
            (
                "a='b\\nc'",
                &[binding(Some("a"), Some("b\\nc"), "a='b\\nc'", 1, false)],
            ),
            (
                "a=\"b\\\"c\"",
                &[binding(Some("a"), Some("b\"c"), "a=\"b\\\"c\"", 1, false)],
            ),
            (
                "a='b\\'c'",
                &[binding(Some("a"), Some("b'c"), "a='b\\'c'", 1, false)],
            ),
            ("a=à", &[binding(Some("a"), Some("à"), "a=à", 1, false)]),
            (
                "a=\"à\"",
                &[binding(Some("a"), Some("à"), "a=\"à\"", 1, false)],
            ),
            (
                "no_value_var",
                &[binding(
                    Some("no_value_var"),
                    None,
                    "no_value_var",
                    1,
                    false,
                )],
            ),
            ("a: b", &[binding(None, None, "a: b", 1, true)]),
            (
                "a=b\nc=d",
                &[
                    binding(Some("a"), Some("b"), "a=b\n", 1, false),
                    binding(Some("c"), Some("d"), "c=d", 2, false),
                ],
            ),
            (
                "a=b\rc=d",
                &[
                    binding(Some("a"), Some("b"), "a=b\r", 1, false),
                    binding(Some("c"), Some("d"), "c=d", 2, false),
                ],
            ),
            (
                "a=b\r\nc=d",
                &[
                    binding(Some("a"), Some("b"), "a=b\r\n", 1, false),
                    binding(Some("c"), Some("d"), "c=d", 2, false),
                ],
            ),
            (
                "a=\nb=c",
                &[
                    binding(Some("a"), Some(""), "a=\n", 1, false),
                    binding(Some("b"), Some("c"), "b=c", 2, false),
                ],
            ),
            ("\n\n", &[binding(None, None, "\n\n", 1, false)]),
            (
                "a=b\n\n",
                &[
                    binding(Some("a"), Some("b"), "a=b\n", 1, false),
                    binding(None, None, "\n", 2, false),
                ],
            ),
            (
                "a=b\n\nc=d",
                &[
                    binding(Some("a"), Some("b"), "a=b\n", 1, false),
                    binding(Some("c"), Some("d"), "\nc=d", 2, false),
                ],
            ),
            (
                "a=\"\nb=c",
                &[
                    binding(None, None, "a=\"\n", 1, true),
                    binding(Some("b"), Some("c"), "b=c", 2, false),
                ],
            ),
            (
                "# comment\na=\"b\nc\"\nd=e\n",
                &[
                    binding(None, None, "# comment\n", 1, false),
                    binding(Some("a"), Some("b\nc"), "a=\"b\nc\"\n", 2, false),
                    binding(Some("d"), Some("e"), "d=e\n", 4, false),
                ],
            ),
            (
                "a=b\n# comment 1",
                &[
                    binding(Some("a"), Some("b"), "a=b\n", 1, false),
                    binding(None, None, "# comment 1", 2, false),
                ],
            ),
            (
                "# comment 1\n# comment 2",
                &[
                    binding(None, None, "# comment 1\n", 1, false),
                    binding(None, None, "# comment 2", 2, false),
                ],
            ),
            (
                "uglyKey[%$=\"S3cr3t_P4ssw#rD\" #\na=b",
                &[
                    binding(
                        Some("uglyKey[%$"),
                        Some("S3cr3t_P4ssw#rD"),
                        "uglyKey[%$=\"S3cr3t_P4ssw#rD\" #\n",
                        1,
                        false,
                    ),
                    binding(Some("a"), Some("b"), "a=b", 2, false),
                ],
            ),
        ];

        for (input, expected) in fixtures {
            assert_eq!(&parse_bindings(input), *expected, "fixture: {input:?}");
        }
    }

    #[test]
    fn interpolation_and_order_match_dotenv_values() {
        let env = HashMap::from([
            ("A".to_owned(), "outside".to_owned()),
            ("OUT".to_owned(), "yes".to_owned()),
        ]);
        let got = parse_and_resolve(
            "A=file\nB=${A}\nC=${MISSING:-fallback}\nD=$A\nE=${OUT}\nNONE\nF=${NONE:-fallback}\n",
            true,
            &env,
        );
        assert_eq!(
            got,
            vec![
                ("A".into(), Some("file".into())),
                ("B".into(), Some("file".into())),
                ("C".into(), Some("fallback".into())),
                ("D".into(), Some("$A".into())),
                ("E".into(), Some("yes".into())),
                ("NONE".into(), None),
                ("F".into(), Some("".into())),
            ]
        );
    }

    #[test]
    fn variable_tokenizer_matches_upstream_regex_edges() {
        assert_eq!(
            parse_variables("hello"),
            vec![VariableAtom::Literal("hello".into())]
        );
        assert_eq!(
            parse_variables("a${name}b${other:-default}c"),
            vec![
                VariableAtom::Literal("a".into()),
                VariableAtom::Variable {
                    name: "name".into(),
                    default: None,
                },
                VariableAtom::Literal("b".into()),
                VariableAtom::Variable {
                    name: "other".into(),
                    default: Some("default".into()),
                },
                VariableAtom::Literal("c".into()),
            ]
        );
        assert_eq!(
            parse_variables("${bad:name}${ok}"),
            vec![
                VariableAtom::Literal("${bad:name}".into()),
                VariableAtom::Variable {
                    name: "ok".into(),
                    default: None,
                },
            ]
        );
        assert_eq!(
            parse_variables("${bad:name${ok}}"),
            vec![
                VariableAtom::Literal("${bad:name".into()),
                VariableAtom::Variable {
                    name: "ok".into(),
                    default: None,
                },
                VariableAtom::Literal("}".into()),
            ]
        );
        assert_eq!(
            parse_variables("${name:-a:b}${}"),
            vec![
                VariableAtom::Variable {
                    name: "name".into(),
                    default: Some("a:b".into()),
                },
                VariableAtom::Variable {
                    name: "".into(),
                    default: None,
                },
            ]
        );
    }

    #[test]
    fn arbitrary_utf8_is_consumed_without_panicking() {
        let alphabet = [
            'A', 'z', '0', '_', '-', '=', ' ', '\t', '\n', '\r', '#', '\'', '"', '\\', '$', '{',
            '}', ':', 'é', '中', '🦀', '\0',
        ];
        let mut state = 0x2026_0811_u64;

        for case_index in 0..10_000 {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            let length = (state as usize) % 256;
            let mut input = String::with_capacity(length);
            for _ in 0..length {
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                input.push(alphabet[(state as usize) % alphabet.len()]);
            }

            let bindings = parse_bindings(&input);
            let reconstructed: String = bindings
                .iter()
                .map(|binding| binding.original.string.as_str())
                .collect();
            assert_eq!(reconstructed, input, "case {case_index}");
            assert!(
                bindings.iter().all(|binding| binding.original.line >= 1),
                "case {case_index}"
            );
        }
    }
}
