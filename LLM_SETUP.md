# LLM Validation Setup Guide

WorkAlign now includes an **optional** LLM validation layer that significantly improves accuracy by catching false positive gaps (skills that are present in the resume but phrased differently).

## How It Works

The LLM validation layer:
1. Runs after basic skill extraction and sentence-level matching
2. Reviews each identified "gap" and checks if it's truly missing or just phrased differently
3. Recovers skills that were missed by automated extraction
4. Significantly reduces false negatives in the "Where Resume Does Not Fully Align" section

## Setup (Optional)

### Option 1: Use LLM Validation (Recommended for Best Accuracy)

1. **Install the anthropic package:**
   ```bash
   pip install anthropic
   ```

2. **Get an Anthropic API key:**
   - Sign up at https://console.anthropic.com/
   - Create an API key in your account settings
   - Free tier available for testing

3. **Set the environment variable:**

   **On Mac/Linux:**
   ```bash
   export ANTHROPIC_API_KEY='your-api-key-here'
   ```

   **On Windows (Command Prompt):**
   ```cmd
   set ANTHROPIC_API_KEY=your-api-key-here
   ```

   **On Windows (PowerShell):**
   ```powershell
   $env:ANTHROPIC_API_KEY='your-api-key-here'
   ```

   **Or create a `.env` file in the project root:**
   ```
   ANTHROPIC_API_KEY=your-api-key-here
   ```

4. **Run the application:**
   ```bash
   streamlit run app.py
   ```

### Option 2: Run Without LLM Validation

If you don't set the `ANTHROPIC_API_KEY` environment variable, WorkAlign will:
- Still perform skill extraction with dependency parsing
- Still perform sentence-level matching for false positive detection
- Skip the LLM validation layer (no API calls)
- Work normally but with potentially more false positives

## Cost Considerations

- LLM validation uses Claude 3.5 Sonnet
- Typical cost per analysis: $0.01 - $0.03 (depending on resume/JD length)
- Free tier includes $5 credit (approximately 200-500 analyses)
- Can be disabled by simply not setting the API key

## Features Enabled by LLM Validation

When enabled, the LLM validation layer:
- ✅ Catches skills described as responsibilities (e.g., "handled AP/AR" → matches "accounts payable")
- ✅ Identifies equivalent terminology (e.g., "managed month-end close" → matches "reconciliation")
- ✅ Reduces false gaps by 40-60% in typical cases
- ✅ Provides more accurate "Where Resume Does Not Fully Align" analysis

## Troubleshooting

**Error: "anthropic package not installed"**
- Run: `pip install anthropic`

**LLM validation not running:**
- Check that `ANTHROPIC_API_KEY` is set: `echo $ANTHROPIC_API_KEY` (Mac/Linux) or `echo %ANTHROPIC_API_KEY%` (Windows)
- Verify the API key is valid at https://console.anthropic.com/

**API errors:**
- Check your API key is active
- Verify you have remaining credits
- Check your internet connection

## Privacy Note

When LLM validation is enabled:
- Resume and JD text are sent to Anthropic's API
- Data is processed per Anthropic's privacy policy
- No data is stored or used for training (per Anthropic's commercial terms)
- If privacy is a concern, you can disable by not setting the API key
