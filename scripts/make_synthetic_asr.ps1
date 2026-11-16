# Render visitor questions with the Windows voices into 16 kHz mono WAVs for a
# SYNTHETIC speech-recognition check. Real recordings (data/eval/asr) are still needed.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/make_synthetic_asr.ps1
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$out = Join-Path $PSScriptRoot "..\data\eval\asr_synthetic"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$phrases = @(
  "where is room eight zero six",
  "where is the xerox shop",
  "how do I get to the library",
  "what is the fee for MCA",
  "is the library open now",
  "where is the health centre",
  "when is the open day",
  "where can I get coffee",
  "how do I apply for admission",
  "what is the reception phone number",
  "where is the accounts office",
  "tell me about the BCA course",
  "where is the department of law",
  "is the college open today",
  "where is professor Sharma",
  "where is the nearest washroom",
  "what courses are there in computer science",
  "where is the MCA lab",
  "I want to talk to a person",
  "where is room eight one two"
)
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$rows = @("file,text,voice")
$voices = @("Microsoft David Desktop", "Microsoft Zira Desktop")
$i = 0
foreach ($v in $voices) {
  foreach ($p in $phrases) {
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.SelectVoice($v)
    $s.Rate = ($i % 3) - 1
    $file = "clip_{0:d3}.wav" -f $i
    $s.SetOutputToWaveFile((Join-Path $out $file), $fmt)
    $s.Speak($p)
    $s.Dispose()
    $rows += "$file,$p,$v"
    $i++
  }
}
$rows | Set-Content -Encoding utf8 (Join-Path $out "transcripts.csv")
Write-Output "Wrote $i clips to $out"
