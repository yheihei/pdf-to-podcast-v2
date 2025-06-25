#!/usr/bin/env python3
import os
import click
import glob
from .utils import setup_logger, Config
from .phases import InputPhase, SplitPhase, ScriptPhase, SynthesizePhase

logger = setup_logger()

@click.group()
@click.option('--env-file', type=click.Path(exists=True), help='Path to .env file')
@click.pass_context
def cli(ctx, env_file):
    """PDF/Text to Podcast Audio Generator"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config.from_env(env_file)
    
    try:
        ctx.obj['config'].validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        click.echo(f"Error: {e}")
        click.echo("Please set GENAI_API_KEY in your .env file")
        ctx.exit(1)

@cli.command()
@click.option('--pdf', type=click.Path(exists=True), help='Input PDF file')
@click.option('--text', type=click.Path(exists=True), help='Input text file')
@click.option('--start', type=int, help='Start page for PDF')
@click.option('--end', type=int, help='End page for PDF')
@click.option('--output-dir', default='output', help='Output directory')
@click.pass_context
def input(ctx, pdf, text, start, end, output_dir):
    """Phase 1: Extract text from PDF or text file"""
    if not pdf and not text:
        click.echo("Error: Please provide either --pdf or --text file")
        return
    
    if pdf and text:
        click.echo("Error: Please provide either --pdf or --text, not both")
        return
    
    phase = InputPhase(output_dir)
    
    try:
        if pdf:
            output_path = phase.process_pdf(pdf, start, end)
        else:
            output_path = phase.process_text(text)
        
        click.echo(f"✓ Text extracted and saved to: {output_path}")
    except Exception as e:
        logger.error(f"Input phase failed: {e}")
        click.echo(f"Error: {e}")
        ctx.exit(1)

@cli.command()
@click.option('--infile', default='output/input_text.txt', help='Input text file')
@click.option('--target-minutes', default=5, help='Target minutes per chunk for audio')
@click.option('--output-dir', default='output/chunks', help='Output directory')
@click.pass_context
def split(ctx, infile, target_minutes, output_dir):
    """Phase 2: Split content into chunks"""
    config = ctx.obj['config']
    phase = SplitPhase(config, output_dir)
    
    try:
        output_paths = phase.process(infile, target_minutes)
        click.echo(f"✓ Content split into {len(output_paths)} chunks")
        for path in output_paths:
            click.echo(f"  - {path}")
    except Exception as e:
        logger.error(f"Split phase failed: {e}")
        click.echo(f"Error: {e}")
        ctx.exit(1)

@cli.command()
@click.option('--indir', default='output/chunks', help='Input directory with chunks')
@click.option('--style', default='親しみやすく', help='Script style')
@click.option('--output-dir', default='output/scripts', help='Output directory')
@click.pass_context
def script(ctx, indir, style, output_dir):
    """Phase 3: Generate scripts from chunks"""
    config = ctx.obj['config']
    phase = ScriptPhase(config, output_dir)
    
    chunk_files = sorted(glob.glob(os.path.join(indir, 'chunk_*.txt')))
    if not chunk_files:
        click.echo(f"Error: No chunk files found in {indir}")
        return
    
    try:
        output_paths = phase.process(chunk_files, style)
        click.echo(f"✓ Generated {len(output_paths)} scripts")
        for path in output_paths:
            click.echo(f"  - {path}")
    except Exception as e:
        logger.error(f"Script phase failed: {e}")
        click.echo(f"Error: {e}")
        ctx.exit(1)

@cli.command()
@click.option('--indir', default='output/scripts', help='Input directory with scripts')
@click.option('--voice', help='Voice name (overrides .env)')
@click.option('--voice-style', help='Voice style (overrides .env)')
@click.option('--output-dir', default='output/audio', help='Output directory')
@click.pass_context
def synthesize(ctx, indir, voice, voice_style, output_dir):
    """Phase 4: Synthesize audio from scripts"""
    config = ctx.obj['config']
    phase = SynthesizePhase(config, output_dir)
    
    script_files = sorted(glob.glob(os.path.join(indir, 'script_*.txt')))
    if not script_files:
        click.echo(f"Error: No script files found in {indir}")
        return
    
    try:
        output_paths = phase.process(script_files, voice, voice_style)
        click.echo(f"✓ Generated {len(output_paths)} audio files")
        for path in output_paths:
            click.echo(f"  - {path}")
    except Exception as e:
        logger.error(f"Synthesize phase failed: {e}")
        click.echo(f"Error: {e}")
        ctx.exit(1)

@cli.command()
@click.option('--pdf', type=click.Path(exists=True), help='Input PDF file')
@click.option('--text', type=click.Path(exists=True), help='Input text file')
@click.option('--start', type=int, help='Start page for PDF')
@click.option('--end', type=int, help='End page for PDF')
@click.option('--voice', help='Voice name')
@click.option('--voice-style', help='Voice style')
@click.option('--target-minutes', default=5, help='Target minutes per chunk')
@click.option('--script-style', default='親しみやすく', help='Script style')
@click.pass_context
def all(ctx, pdf, text, start, end, voice, voice_style, target_minutes, script_style):
    """Run all phases sequentially"""
    if not pdf and not text:
        click.echo("Error: Please provide either --pdf or --text file")
        return
    
    config = ctx.obj['config']
    
    click.echo("=== Phase 1: Input Processing ===")
    input_phase = InputPhase()
    try:
        if pdf:
            input_file = input_phase.process_pdf(pdf, start, end)
        else:
            input_file = input_phase.process_text(text)
        click.echo(f"✓ Input processed")
    except Exception as e:
        click.echo(f"✗ Input phase failed: {e}")
        return
    
    click.echo("\n=== Phase 2: Content Splitting ===")
    split_phase = SplitPhase(config)
    try:
        chunk_files = split_phase.process(input_file, target_minutes)
        click.echo(f"✓ Split into {len(chunk_files)} chunks")
    except Exception as e:
        click.echo(f"✗ Split phase failed: {e}")
        return
    
    click.echo("\n=== Phase 3: Script Generation ===")
    script_phase = ScriptPhase(config)
    try:
        script_files = script_phase.process(chunk_files, script_style)
        click.echo(f"✓ Generated {len(script_files)} scripts")
    except Exception as e:
        click.echo(f"✗ Script phase failed: {e}")
        return
    
    click.echo("\n=== Phase 4: Audio Synthesis ===")
    synthesize_phase = SynthesizePhase(config)
    try:
        audio_files = synthesize_phase.process(script_files, voice, voice_style)
        click.echo(f"✓ Generated {len(audio_files)} audio files")
        
        click.echo("\n=== Complete ===")
        click.echo("Audio files generated:")
        for audio in audio_files:
            click.echo(f"  - {audio}")
    except Exception as e:
        click.echo(f"✗ Synthesize phase failed: {e}")
        return

if __name__ == '__main__':
    cli()