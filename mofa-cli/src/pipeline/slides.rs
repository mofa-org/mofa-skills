// SPDX-License-Identifier: Apache-2.0

use crate::config::MofaConfig;
use crate::dashscope::DashscopeClient;
use crate::deepseek_ocr::DeepSeekOcrClient;
use crate::gemini::GeminiClient;
use crate::layout::{
    extract_text_layout, extract_text_layout_deepseek, extract_text_layout_ocr,
    refine_text_layout, NO_TEXT_INSTRUCTION, SH, SW,
};
use crate::pptx::{self, SlideData, TextOverlay};
use crate::style::Style;
use eyre::Result;
use serde::Deserialize;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

/// Input slide definition (from JSON).
#[derive(Deserialize, Debug)]
pub struct SlideInput {
    pub prompt: String,
    pub style: Option<String>,
    pub texts: Option<Vec<TextOverlay>>,
    #[serde(default)]
    pub auto_layout: bool,
    pub images: Option<Vec<String>>,
    pub gen_model: Option<String>,
    /// Path to an existing image to use as-is (skip generation).
    /// VQA text extraction + Qwen-Edit text removal still apply when auto_layout=true.
    /// This enables PDF-to-PPTX conversion: provide original page images, extract text,
    /// remove text, overlay editable text.
    pub source_image: Option<String>,
}

/// Full slides pipeline: generate images + build multi-slide PPTX.
#[allow(clippy::too_many_arguments)]
pub fn run(
    slide_dir: &Path,
    out_file: &Path,
    slides: &[SlideInput],
    style: &Style,
    cfg: &MofaConfig,
    concurrency: usize,
    image_size: Option<&str>,
    gen_model: Option<&str>,
    ref_image_size: Option<&str>,
    vision_model: Option<&str>,
    refine_with_qwen: bool,
) -> Result<()> {
    let gemini_key = cfg
        .gemini_key()
        .ok_or_else(|| eyre::eyre!("Gemini API key required"))?;
    let gemini = GeminiClient::new(gemini_key);

    // Build DeepSeek-OCR-2 client for local OCR with grounding
    let deepseek_ocr = match cfg.deepseek_ocr_url() {
        Some(url) => {
            eprintln!("DeepSeek-OCR-2 enabled: {url}");
            Some(DeepSeekOcrClient::new(url))
        }
        None => None,
    };

    // Build Dashscope client for OCR text extraction + optional Qwen-Edit refinement
    let dashscope = match cfg.dashscope_key() {
        Some(key) => {
            eprintln!(
                "Dashscope enabled (OCR{})",
                if refine_with_qwen { " + Qwen-Edit" } else { "" }
            );
            Some(DashscopeClient::new(key))
        }
        None => {
            if refine_with_qwen {
                eprintln!("Warning: --refine requested but DASHSCOPE_API_KEY not set");
            }
            None
        }
    };

    std::fs::create_dir_all(slide_dir)?;
    let total = slides.len();
    eprintln!("Generating {total} slides ({concurrency} parallel)...");

    // Phase 1+2: Generate ref images and extract text (parallel)
    let ref_paths: Arc<Mutex<Vec<Option<PathBuf>>>> =
        Arc::new(Mutex::new(vec![None; total]));
    let extracted_texts: Arc<Mutex<Vec<Option<Vec<TextOverlay>>>>> =
        Arc::new(Mutex::new(vec![None; total]));
    // For non-autoLayout slides, store final paths directly
    let direct_paths: Arc<Mutex<Vec<Option<PathBuf>>>> =
        Arc::new(Mutex::new(vec![None; total]));

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(concurrency)
        .build()?;

    pool.scope(|s| {
        for (idx, slide) in slides.iter().enumerate() {
            let gemini = &gemini;
            let dashscope = &dashscope;
            let deepseek_ocr = &deepseek_ocr;
            let ref_paths = Arc::clone(&ref_paths);
            let extracted_texts = Arc::clone(&extracted_texts);
            let direct_paths = Arc::clone(&direct_paths);

            s.spawn(move |_| {
                let variant = slide.style.as_deref().unwrap_or("normal");
                let prefix = style.get_prompt(variant);
                let padded = format!("{:02}", idx + 1);
                let model = slide
                    .gen_model
                    .as_deref()
                    .or(gen_model)
                    .unwrap_or(cfg.gen_model());

                let ref_images: Vec<&Path> = slide
                    .images
                    .as_ref()
                    .map(|imgs| imgs.iter().map(|p| Path::new(p.as_str())).collect())
                    .unwrap_or_default();

                if slide.auto_layout {
                    // Phase 1: Get reference image (generate or use source_image)
                    let ref_file = slide_dir.join(format!("slide-{padded}-ref.png"));

                    let ref_ready = if let Some(ref src) = slide.source_image {
                        // Use existing image — copy to ref_file location
                        let src_path = Path::new(src);
                        if src_path.exists() {
                            if let Err(e) = std::fs::copy(src_path, &ref_file) {
                                eprintln!("Slide {}: failed to copy source image — {e}", idx + 1);
                                false
                            } else {
                                eprintln!("Slide {} (source): {}", idx + 1, src);
                                true
                            }
                        } else {
                            eprintln!("Slide {}: source_image not found: {src}", idx + 1);
                            false
                        }
                    } else {
                        // Generate WITH text (reference image)
                        let full_prompt = format!("{prefix}\n\n{}", slide.prompt);
                        let ref_size = ref_image_size.or(image_size);
                        matches!(
                            gemini.gen_image(
                                &full_prompt,
                                &ref_file,
                                ref_size,
                                Some("16:9"),
                                &ref_images,
                                Some(model),
                                Some(&format!("Slide {} (ref)", idx + 1)),
                            ),
                            Ok(Some(_))
                        )
                    };

                    if ref_ready {
                        // Phase 2: Extract text positions
                        // Priority: DeepSeek-OCR-2 (local, grounding) > Dashscope OCR > Gemini VQA
                        let extraction_result = if let Some(ref ds_ocr) = deepseek_ocr {
                            match extract_text_layout_deepseek(
                                ds_ocr, gemini, &ref_file, SW, SH, vision_model,
                            ) {
                                Ok(texts) if !texts.is_empty() => {
                                    eprintln!(
                                        "Slide {}: DeepSeek-OCR extracted {} text blocks",
                                        idx + 1, texts.len()
                                    );
                                    Ok((texts, true)) // true = used OCR (skip refinement)
                                }
                                Ok(_) => {
                                    eprintln!(
                                        "Slide {}: DeepSeek-OCR returned empty, falling back",
                                        idx + 1
                                    );
                                    // Fall through to Dashscope/VQA
                                    Err(eyre::eyre!("empty"))
                                }
                                Err(e) => {
                                    eprintln!(
                                        "Slide {}: DeepSeek-OCR failed ({e}), falling back",
                                        idx + 1
                                    );
                                    Err(e)
                                }
                            }
                        } else {
                            Err(eyre::eyre!("no deepseek"))
                        };

                        // Fallback: Dashscope OCR or Gemini VQA
                        let extraction_result = if extraction_result.is_ok() {
                            extraction_result
                        } else if let Some(ref ds) = dashscope {
                            match extract_text_layout_ocr(
                                ds, gemini, &ref_file, SW, SH, vision_model, Some(prefix),
                            ) {
                                Ok(texts) => {
                                    eprintln!(
                                        "Slide {}: Dashscope OCR extracted {} text blocks",
                                        idx + 1, texts.len()
                                    );
                                    Ok((texts, true))
                                }
                                Err(e) => {
                                    eprintln!(
                                        "Slide {}: Dashscope OCR failed ({e}), falling back to VQA",
                                        idx + 1
                                    );
                                    extract_text_layout(
                                        gemini, &ref_file, SW, SH, vision_model, Some(prefix),
                                    ).map(|t| (t, false))
                                }
                            }
                        } else {
                            extract_text_layout(
                                gemini, &ref_file, SW, SH, vision_model, Some(prefix),
                            ).map(|t| (t, false))
                        };

                        match extraction_result {
                            Ok((texts, used_ocr)) => {
                                eprintln!(
                                    "Slide {}: extracted {} text elements ({})",
                                    idx + 1, texts.len(),
                                    if used_ocr { "OCR" } else { "VQA" }
                                );
                                // Only refine if VQA was used (OCR positions are precise)
                                let texts = if !used_ocr {
                                    match refine_text_layout(
                                        gemini, &ref_file, &texts, SW, SH, vision_model,
                                    ) {
                                        Ok(refined) => {
                                            eprintln!(
                                                "Slide {}: refined {} text elements",
                                                idx + 1, refined.len()
                                            );
                                            refined
                                        }
                                        Err(e) => {
                                            eprintln!(
                                                "Slide {}: refinement failed ({e}), using initial",
                                                idx + 1
                                            );
                                            texts
                                        }
                                    }
                                } else {
                                    texts
                                };
                                extracted_texts.lock().unwrap()[idx] = Some(texts);
                            }
                            Err(e) => {
                                eprintln!("Slide {}: text extraction failed — {e}", idx + 1);
                            }
                        }
                        ref_paths.lock().unwrap()[idx] = Some(ref_file);
                    }
                } else {
                    // Standard flow: baked text or manual overlays
                    let mut full_prompt = format!("{prefix}\n\n{}", slide.prompt);
                    if slide.texts.is_some() {
                        full_prompt.push_str(NO_TEXT_INSTRUCTION);
                    }

                    let out_path = slide_dir.join(format!("slide-{padded}.png"));
                    if let Ok(Some(p)) = gemini.gen_image(
                        &full_prompt,
                        &out_path,
                        image_size,
                        Some("16:9"),
                        &ref_images,
                        Some(model),
                        Some(&format!("Slide {}", idx + 1)),
                    ) {
                        direct_paths.lock().unwrap()[idx] = Some(p);
                    }
                }
            });
        }
    });

    // Phase 3: Generate clean images (sequential for Qwen-Edit, parallel for Gemini)
    let ref_paths = ref_paths.lock().unwrap().clone();
    let direct_paths = direct_paths.lock().unwrap().clone();
    let mut final_paths: Vec<Option<PathBuf>> = vec![None; total];

    #[allow(clippy::needless_range_loop)]
    for idx in 0..total {
        if !slides[idx].auto_layout {
            final_paths[idx] = direct_paths[idx].clone();
            continue;
        }
        let Some(ref ref_path) = ref_paths[idx] else {
            continue;
        };

        let padded = format!("{:02}", idx + 1);
        let out_path = slide_dir.join(format!("slide-{padded}.png"));

        // OCR-guided mask edit: OCR → mask → wanx2.1 inpainting.
        // Falls back to Qwen-Edit, then Gemini regeneration.
        if let Some(ref ds) = dashscope {
            eprintln!("Slide {}: removing text with OCR-guided mask edit...", idx + 1);
            match ds.remove_text(ref_path, &out_path) {
                Ok(p) => {
                    final_paths[idx] = Some(p);
                    continue;
                }
                Err(e) => {
                    eprintln!("Slide {}: mask edit failed ({e}), trying Qwen-Edit...", idx + 1);
                    match ds.refine_image(
                        ref_path,
                        "Remove all readable text, numbers, and punctuation from this image. \
                         Replace removed text with surrounding background. Keep all non-text elements.",
                        &out_path,
                        Some(cfg.edit_model()),
                    ) {
                        Ok(p) => {
                            final_paths[idx] = Some(p);
                            continue;
                        }
                        Err(e2) => {
                            eprintln!("Slide {}: Qwen-Edit also failed ({e2}), falling back to Gemini", idx + 1);
                        }
                    }
                }
            }
        }

        // Edit the ref image: pass it as reference with a "remove text" instruction.
        // This preserves the exact layout while removing all text.
        // Key: the prompt contains NO slide text content — only an editing instruction.
        let model = slides[idx]
            .gen_model
            .as_deref()
            .or(gen_model)
            .unwrap_or(cfg.gen_model());
        let clean_prompt = "\
            Edit this presentation slide image. Remove ALL text from the image — \
            every title, heading, subtitle, body text, label, number, date, stat, \
            caption, bullet point, table header, table cell content, card title, \
            axis label, and any other readable characters. \
            Replace each text area with the surrounding background color or pattern \
            so the area looks naturally empty. \
            Keep ALL non-text visual elements EXACTLY as they are: \
            shapes, cards, panels, borders, lines, icons, wireframes, gradients, \
            arrows, decorative elements, colors, layout structure. \
            The output must look identical to the input but with ZERO readable text anywhere."
            .to_string();
        let ref_images: Vec<&Path> = vec![ref_path.as_path()];

        if let Ok(Some(p)) = gemini.gen_image(
            &clean_prompt,
            &out_path,
            image_size,
            Some("16:9"),
            &ref_images,
            Some(model),
            Some(&format!("Slide {} (clean)", idx + 1)),
        ) {
            final_paths[idx] = Some(p);
        }
    }

    // Build slide data
    let extracted = extracted_texts.lock().unwrap();

    let slide_data: Vec<SlideData> = (0..total)
        .map(|i| {
            let image_path = final_paths[i].as_ref().map(|p| p.to_string_lossy().to_string());
            let texts = if slides[i].auto_layout {
                extracted[i].clone().unwrap_or_default()
            } else {
                slides[i].texts.clone().unwrap_or_default()
            };
            SlideData { image_path, texts }
        })
        .collect();

    pptx::build_pptx(&slide_data, out_file, SW, SH)?;
    let ok = final_paths.iter().filter(|p| p.is_some()).count();
    eprintln!("\nDone: {out_file} ({ok}/{total} slides)", out_file = out_file.display());
    Ok(())
}
