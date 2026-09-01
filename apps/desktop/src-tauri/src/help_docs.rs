//! Integrierte Hilfe (Plan projektfenster.md, P6b, Vorbild tec-e2e):
//! die Hilfe rendert die Markdown-Dateien des Repos — keine zweite
//! Doku, die veraltet. Anders als im Vorbild sind die Inhalte hier
//! **einkompiliert** (`include_str!`), weil die verteilte App kein
//! Repo neben sich hat; der angezeigte Quellpfad sagt trotzdem, welche
//! Datei man ändert. Feste Slug-Tabelle statt freier Pfade — `help_doc`
//! kann nur registrierte Dokumente liefern.

use serde::Serialize;

struct HelpDoc {
    slug: &'static str,
    title: &'static str,
    description: &'static str,
    /// Repo-Pfad der Quelle — wird über dem Text angezeigt.
    source_path: &'static str,
    content: &'static str,
}

const DOCS: &[HelpDoc] = &[
    HelpDoc {
        slug: "app-bedienen",
        title: "Die App bedienen",
        description: "Der schnelle Weg, die Tabs, Fragen beantworten, was tun wenn etwas klemmt.",
        source_path: "docs/app-bedienen.md",
        content: include_str!("../../../../docs/app-bedienen.md"),
    },
    HelpDoc {
        slug: "workflow-regeln",
        title: "Der Board-Workflow (Agenten-Regeln)",
        description: "Der Policy-Text, den Einrichten ins Projekt legt — was der Agent am Board tut.",
        source_path: "apps/desktop/src-tauri/templates/workflow-policy.md",
        content: include_str!("../templates/workflow-policy.md"),
    },
    HelpDoc {
        slug: "projekt-ueberblick",
        title: "Was Speccify ist",
        description: "Skills, Tool-Verträge und der Dreischritt Expand/Execute/Evaluate — der Repo-Überblick.",
        source_path: "README.md",
        content: include_str!("../../../../README.md"),
    },
    HelpDoc {
        slug: "git-quellen",
        title: "Skills über Git teilen",
        description: "Skill-Quellen als Git-Repos, Versionen über Tags, Discovery über Index-Repos.",
        source_path: "docs/git-sources.md",
        content: include_str!("../../../../docs/git-sources.md"),
    },
    HelpDoc {
        slug: "toolkit",
        title: "Die lokalen MCP-Server",
        description: "Exec, Discovery und Owner-Fragen — was die App für externe Clients bereitstellt.",
        source_path: "docs/toolkit.md",
        content: include_str!("../../../../docs/toolkit.md"),
    },
];

#[derive(Serialize)]
pub struct HelpDocMeta {
    slug: String,
    title: String,
    description: String,
    source_path: String,
}

#[tauri::command]
pub fn help_docs() -> Vec<HelpDocMeta> {
    DOCS.iter()
        .map(|doc| HelpDocMeta {
            slug: doc.slug.into(),
            title: doc.title.into(),
            description: doc.description.into(),
            source_path: doc.source_path.into(),
        })
        .collect()
}

#[tauri::command]
pub fn help_doc(slug: String) -> Result<String, String> {
    DOCS.iter()
        .find(|doc| doc.slug == slug)
        .map(|doc| doc.content.to_string())
        .ok_or_else(|| format!("Unbekanntes Hilfe-Dokument: {slug}"))
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Redaktions-Contract wie im tec-e2e-Vorbild.
    #[test]
    fn registry_is_well_formed() {
        let mut slugs = std::collections::HashSet::new();
        for doc in DOCS {
            assert!(slugs.insert(doc.slug), "Slug doppelt: {}", doc.slug);
            assert!(
                doc.description.len() > 20,
                "Beschreibung zu knapp: {}",
                doc.slug
            );
            assert!(
                !doc.source_path.contains("..") && !doc.source_path.starts_with('/'),
                "Quellpfad verlässt das Repo: {}",
                doc.source_path
            );
            assert!(
                !doc.content.trim().is_empty(),
                "Leerer Inhalt: {}",
                doc.slug
            );
        }
        assert!(help_doc("app-bedienen".into())
            .unwrap()
            .contains("## Der schnelle Weg"));
        assert!(help_doc("gibts-nicht".into()).is_err());
    }
}
