// SPDX-License-Identifier: Apache-2.0

use crate::config::MofaConfig;
use crate::gemini::GeminiClient;
use crate::style::Style;
use eyre::Result;
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

/// Input card definition (from JSON).
#[derive(Deserialize, Debug)]
pub struct CardInput {
    pub name: String,
    pub prompt: String,
    pub style: Option<String>,
}

/// Card pipeline: generate PNG greeting cards in parallel.
#[allow(clippy::too_many_arguments)]
pub fn run(
    card_dir: &Path,
    cards: &[CardInput],
    style: &Style,
    cfg: &MofaConfig,
    concurrency: usize,
    aspect_ratio: Option<&str>,
    image_size: Option<&str>,
    gen_model: Option<&str>,
) -> Result<Vec<Option<PathBuf>>> {
    let gemini_key = cfg
        .gemini_key()
        .ok_or_else(|| eyre::eyre!("Gemini API key required"))?;
    let gemini = GeminiClient::new(gemini_key);

    std::fs::create_dir_all(card_dir)?;
    let total = cards.len();
    let ar = aspect_ratio.unwrap_or(
        cfg.defaults
            .cards
            .as_ref()
            .and_then(|c| c.aspect_ratio.as_deref())
            .unwrap_or("9:16"),
    );
    let size = image_size.or(
        cfg.defaults
            .cards
            .as_ref()
            .and_then(|c| c.image_size.as_deref()),
    );
    let model = gen_model.unwrap_or(cfg.gen_model());

    eprintln!("Generating {total} cards ({concurrency} parallel, {ar})...");

    let paths: Arc<Mutex<Vec<Option<PathBuf>>>> =
        Arc::new(Mutex::new(vec![None; total]));

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(concurrency)
        .build()?;

    pool.scope(|s| {
        for (idx, card) in cards.iter().enumerate() {
            let gemini = &gemini;
            let paths = Arc::clone(&paths);

            s.spawn(move |_| {
                let variant = card.style.as_deref().unwrap_or("front");
                let prefix = style.get_prompt(variant);
                let full_prompt = format!("{prefix}\n\n{}", card.prompt);
                let out_path = card_dir.join(format!("card-{}.png", card.name));

                if let Ok(Some(p)) = gemini.gen_image(
                    &full_prompt,
                    &out_path,
                    size,
                    Some(ar),
                    &[],
                    Some(model),
                    Some(&card.name),
                ) {
                    paths.lock().unwrap()[idx] = Some(p);
                }
            });
        }
    });

    let result = paths.lock().unwrap().clone();
    let ok = result.iter().filter(|p| p.is_some()).count();
    eprintln!("\nDone: {ok}/{total} cards in {}/", card_dir.display());
    Ok(result)
}
