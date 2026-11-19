# Official source extracts — accessed 2026-11-19

These are public documentation checks, not authenticated model-availability or billing checks. Full research tool observations are retained in the sanitized research-agent conversation. The parent also fetched and checked the sources below.

## Text model

URL: https://developers.openai.com/api/docs/models/gpt-4o-mini

> Model ID: `gpt-4o-mini`
> Status: Deprecated
> Default snapshot: `gpt-4o-mini-2024-07-18`
> 128,000 context window
> 16,384 max output tokens

Text-token table: Input $0.15 / 1M tokens; cached input $0.075 / 1M tokens; output $0.6 / 1M tokens. Chat Completions supported; function_calling listed. Cross-check: https://developers.openai.com/api/docs/pricing lists the same standard rates.

Chat Completions parameter reference: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create

Research verified `max_completion_tokens` as an output upper bound, `max_tokens` deprecated, and standard/default tier selection. Parameter acceptance and actual billing were not exercised.

## Current Realtime candidate

URL: https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini

> Model ID: `gpt-realtime-2.1-mini`
> Default snapshot: `gpt-realtime-2.1-mini`
> Input modalities: text, audio, image
> Output modalities: text, audio
> 128,000 context window
> 32,000 max output tokens
> Reasoning token support

Text-token table per 1M tokens: input $0.6; cached input $0.06; output $2.4.
Audio-token table per 1M tokens: input $10; cached input $0.3; output $20.
Realtime endpoint supported; Chat Completions and separate speech-generation/transcription endpoints not supported for this model. No separate dated snapshot is listed. Image rates are not used because image requests are blocked.

## Current separate STT option

URL: https://developers.openai.com/api/docs/models/gpt-transcribe

> Model ID: `gpt-transcribe`
> Default snapshot: `gpt-transcribe`

Transcription audio-duration table: $0.0045 / minute. File transcription and Realtime transcription endpoints supported. This is a documented option, not an integration or approved audio batch.

## Separate STT/TTS comparisons

Pricing URL: https://developers.openai.com/api/docs/pricing

- `gpt-4o-mini-transcribe`: input $1.25, output $5.00, estimated $0.003 / minute. Do not convert an estimate into a hard cap.
- `gpt-4o-mini-tts`: audio output $12.00 / 1M tokens; text input $0.60 / 1M tokens.
- `tts-1`: $15.00 / 1M input characters.
- Whisper: $0.006 / minute.

Model snapshots/status and announced shutdown dates were checked by the research agent against the model pages and these guides:
https://developers.openai.com/api/docs/guides/speech-to-text
https://developers.openai.com/api/docs/guides/text-to-speech

Retain the deprecation warnings in `model_and_spending_plan.md`; none of these comparisons enables a paid model. Realtime cost-guide URL: https://developers.openai.com/api/docs/guides/realtime-costs . Audio-token approximations and history replay do not yield a hard total-spend bound from input duration alone.

## LiveKit billing boundary

URL: https://docs.livekit.io/agents/models/realtime/plugins/openai/

> With LiveKit Inference, you use your LiveKit Cloud credentials instead of a separate OpenAI API key, and LiveKit Cloud bills you for usage. Use the plugin instead if you want to manage your own billing.

> Use the OpenAI plugin to connect directly to the OpenAI Realtime API with your own API key.

Python install shown: `uv add "livekit-agents[openai]~=1.8"`. This was not run. The plugin model default is documented as `gpt-realtime`; do not confuse that legacy default with the newer candidate above. The current Inference table includes `openai/gpt-realtime-2.1-mini`, but Inference would bill LiveKit, not the user's OpenAI credit.

URL: https://docs.livekit.io/transport/self-hosting/local/

macOS install example: `brew update && brew install livekit`; development server: `livekit-server --dev`. Default bind: `127.0.0.1:7880`. No install/server startup was performed.

URL: https://livekit.io/pricing

> No credit card required • 1,000 free agent session minutes monthly

This advertisement is not proof of plan activation, unlimited transport/inference or telephony coverage. No LiveKit Cloud, Deepgram, Cartesia or carrier allocation was approved. OpenAI credit is separate.
