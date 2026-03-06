// SPDX-License-Identifier: Apache-2.0

mod config;
mod dashscope;
mod deepseek_ocr;
mod gemini;
mod image_util;
mod layout;
mod pipeline;
mod pptx;
mod style;
mod veo;

use clap::{Parser, Subcommand};
use eyre::Result;
use std::io::Read;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "mofa", about = "AI-powered content generation CLI")]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Path to mofa root directory (auto-detected if omitted)
    #[arg(long, global = true)]
    root: Option<PathBuf>,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate a multi-slide PPTX presentation
    Slides {
        /// Style name (from styles/ directory)
        #[arg(long, default_value = "nb-pro")]
        style: String,
        /// Output PPTX file
        #[arg(long, short)]
        out: PathBuf,
        /// Directory for intermediate slide PNGs
        #[arg(long)]
        slide_dir: PathBuf,
        /// Parallel generation limit
        #[arg(long, default_value = "5")]
        concurrency: usize,
        /// Image size: 1K, 2K, 4K
        #[arg(long)]
        image_size: Option<String>,
        /// Gemini model override
        #[arg(long)]
        gen_model: Option<String>,
        /// Lower-res image size for autoLayout Phase 1 reference images
        #[arg(long)]
        ref_image_size: Option<String>,
        /// Vision model for autoLayout text extraction
        #[arg(long)]
        vision_model: Option<String>,
        /// Enable editable text mode: extract text, clean background, overlay text boxes
        #[arg(long)]
        auto_layout: bool,
        /// Use Qwen-Edit to remove text from reference images (cleaner output)
        #[arg(long)]
        refine: bool,
        /// Input JSON file (or stdin if omitted)
        #[arg(long, short)]
        input: Option<PathBuf>,
    },
    /// Generate PNG greeting/holiday cards
    Cards {
        /// Style name
        #[arg(long, default_value = "cny-guochao")]
        style: String,
        /// Directory for card PNGs
        #[arg(long)]
        card_dir: PathBuf,
        /// Aspect ratio
        #[arg(long)]
        aspect: Option<String>,
        /// Parallel generation limit
        #[arg(long, default_value = "5")]
        concurrency: usize,
        /// Image size: 1K, 2K, 4K
        #[arg(long)]
        image_size: Option<String>,
        /// Input JSON file (or stdin)
        #[arg(long, short)]
        input: Option<PathBuf>,
    },
    /// Generate a multi-panel comic strip
    Comic {
        /// Style name
        #[arg(long, default_value = "xkcd")]
        style: String,
        /// Output PNG file
        #[arg(long, short)]
        out: PathBuf,
        /// Working directory for panel PNGs
        #[arg(long)]
        work_dir: Option<PathBuf>,
        /// Layout: horizontal, vertical, grid
        #[arg(long, default_value = "horizontal")]
        layout: String,
        /// Parallel generation limit
        #[arg(long, default_value = "3")]
        concurrency: usize,
        /// Image size
        #[arg(long)]
        image_size: Option<String>,
        /// Refine panels with Qwen-Edit
        #[arg(long)]
        refine: bool,
        /// Gap between panels in pixels
        #[arg(long, default_value = "20")]
        gutter: u32,
        /// Input JSON file (or stdin)
        #[arg(long, short)]
        input: Option<PathBuf>,
    },
    /// Generate a multi-section infographic
    Infographic {
        /// Style name
        #[arg(long, default_value = "cyberpunk-neon")]
        style: String,
        /// Output PNG file
        #[arg(long, short)]
        out: PathBuf,
        /// Working directory for section PNGs
        #[arg(long)]
        work_dir: Option<PathBuf>,
        /// Parallel generation limit
        #[arg(long, default_value = "3")]
        concurrency: usize,
        /// Image size
        #[arg(long)]
        image_size: Option<String>,
        /// Aspect ratio per section
        #[arg(long)]
        aspect: Option<String>,
        /// Refine sections with Qwen-Edit
        #[arg(long)]
        refine: bool,
        /// Gap between sections in pixels
        #[arg(long, default_value = "0")]
        gutter: u32,
        /// Input JSON file (or stdin)
        #[arg(long, short)]
        input: Option<PathBuf>,
    },
    /// Generate animated video cards with Veo
    Video {
        /// Image style name
        #[arg(long, default_value = "video-card")]
        style: String,
        /// Animation style name
        #[arg(long, default_value = "shuimo")]
        anim_style: String,
        /// Directory for PNGs and MP4s
        #[arg(long)]
        card_dir: PathBuf,
        /// Background music file
        #[arg(long)]
        bgm: Option<PathBuf>,
        /// Aspect ratio for images
        #[arg(long, default_value = "9:16")]
        aspect: String,
        /// Image size
        #[arg(long)]
        image_size: Option<String>,
        /// Parallel limit for image gen
        #[arg(long, default_value = "3")]
        concurrency: usize,
        /// Still image duration (seconds)
        #[arg(long, default_value = "2.0")]
        still_duration: f64,
        /// Crossfade duration (seconds)
        #[arg(long, default_value = "1.0")]
        crossfade_dur: f64,
        /// Fade out duration (seconds)
        #[arg(long, default_value = "1.5")]
        fade_out_dur: f64,
        /// Music volume (0.0-1.0)
        #[arg(long, default_value = "0.3")]
        music_volume: f64,
        /// Music fade in duration (seconds)
        #[arg(long, default_value = "2.0")]
        music_fade_in: f64,
        /// Input JSON file (or stdin)
        #[arg(long, short)]
        input: Option<PathBuf>,
    },
}

fn read_input(path: Option<&PathBuf>) -> Result<String> {
    match path {
        Some(p) => Ok(std::fs::read_to_string(p)?),
        None => {
            let mut buf = String::new();
            std::io::stdin().read_to_string(&mut buf)?;
            Ok(buf)
        }
    }
}

fn find_styles_dir(mofa_root: &std::path::Path, skill_name: &str) -> PathBuf {
    // Try mofa-<skill>/styles/ first, then mofa/styles/
    let skill_styles = mofa_root.join(format!("mofa-{skill_name}")).join("styles");
    if skill_styles.exists() {
        return skill_styles;
    }
    mofa_root.join("mofa").join("styles")
}

fn main() -> Result<()> {
    color_eyre::install()?;
    let cli = Cli::parse();

    let mofa_root = cli.root.unwrap_or_else(config::find_mofa_root);
    let cfg = config::MofaConfig::load_default(&mofa_root);

    match cli.command {
        Commands::Slides {
            style: style_name,
            out,
            slide_dir,
            concurrency,
            image_size,
            gen_model,
            ref_image_size,
            vision_model,
            auto_layout,
            refine,
            input,
        } => {
            let styles_dir = find_styles_dir(&mofa_root, "slides");
            let style_file = styles_dir.join(format!("{style_name}.toml"));
            let loaded_style = style::load_style(&style_file)?;

            let json = read_input(input.as_ref())?;
            let mut slides: Vec<pipeline::slides::SlideInput> = serde_json::from_str(&json)?;

            // --auto-layout flag overrides all slides
            if auto_layout {
                for slide in &mut slides {
                    slide.auto_layout = true;
                }
            }

            pipeline::slides::run(
                &slide_dir,
                &out,
                &slides,
                &loaded_style,
                &cfg,
                concurrency,
                image_size.as_deref(),
                gen_model.as_deref(),
                ref_image_size.as_deref(),
                vision_model.as_deref(),
                refine,
            )?;
        }
        Commands::Cards {
            style: style_name,
            card_dir,
            aspect,
            concurrency,
            image_size,
            input,
        } => {
            let styles_dir = find_styles_dir(&mofa_root, "cards");
            let style_file = styles_dir.join(format!("{style_name}.toml"));
            let loaded_style = style::load_style(&style_file)?;

            let json = read_input(input.as_ref())?;
            let cards: Vec<pipeline::cards::CardInput> = serde_json::from_str(&json)?;

            pipeline::cards::run(
                &card_dir,
                &cards,
                &loaded_style,
                &cfg,
                concurrency,
                aspect.as_deref(),
                image_size.as_deref(),
                None,
            )?;
        }
        Commands::Comic {
            style: style_name,
            out,
            work_dir,
            layout,
            concurrency,
            image_size,
            refine,
            gutter,
            input,
        } => {
            let styles_dir = find_styles_dir(&mofa_root, "comic");
            let style_file = styles_dir.join(format!("{style_name}.toml"));
            let loaded_style = style::load_style(&style_file)?;

            let out_dir = work_dir.unwrap_or_else(|| {
                out.parent().unwrap_or(std::path::Path::new(".")).to_path_buf()
            });

            let json = read_input(input.as_ref())?;
            let panels: Vec<pipeline::comic::PanelInput> = serde_json::from_str(&json)?;

            pipeline::comic::run(
                &out_dir,
                &out,
                &panels,
                &loaded_style,
                &cfg,
                &layout,
                concurrency,
                image_size.as_deref(),
                refine,
                gutter,
                None,
            )?;
        }
        Commands::Infographic {
            style: style_name,
            out,
            work_dir,
            concurrency,
            image_size,
            aspect,
            refine,
            gutter,
            input,
        } => {
            let styles_dir = find_styles_dir(&mofa_root, "infographic");
            let style_file = styles_dir.join(format!("{style_name}.toml"));
            let loaded_style = style::load_style(&style_file)?;

            let out_dir = work_dir.unwrap_or_else(|| {
                out.parent().unwrap_or(std::path::Path::new(".")).to_path_buf()
            });

            let json = read_input(input.as_ref())?;
            let sections: Vec<pipeline::infographic::SectionInput> =
                serde_json::from_str(&json)?;

            pipeline::infographic::run(
                &out_dir,
                &out,
                &sections,
                &loaded_style,
                &cfg,
                concurrency,
                image_size.as_deref(),
                aspect.as_deref(),
                refine,
                gutter,
                None,
            )?;
        }
        Commands::Video {
            style: style_name,
            anim_style: anim_style_name,
            card_dir,
            bgm,
            aspect,
            image_size,
            concurrency,
            still_duration,
            crossfade_dur,
            fade_out_dur,
            music_volume,
            music_fade_in,
            input,
        } => {
            let styles_dir = find_styles_dir(&mofa_root, "video");
            let img_style_file = styles_dir.join(format!("{style_name}.toml"));
            let img_style = style::load_style(&img_style_file)?;

            let anim_style_file = styles_dir.join(format!("{anim_style_name}.toml"));
            let anim_style = if anim_style_file.exists() {
                style::load_style(&anim_style_file)?
            } else {
                style::load_style(&img_style_file)?
            };

            let json = read_input(input.as_ref())?;
            let cards: Vec<pipeline::video::VideoCardInput> = serde_json::from_str(&json)?;

            pipeline::video::run(
                &card_dir,
                &cards,
                &img_style,
                &anim_style,
                &cfg,
                concurrency,
                Some(&aspect),
                image_size.as_deref(),
                bgm.as_deref(),
                still_duration,
                crossfade_dur,
                fade_out_dur,
                music_volume,
                music_fade_in,
            )?;
        }
    }

    Ok(())
}
