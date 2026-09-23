import {createOpenAI} from './openai.js';
import {createGemini} from './gemini.js';

export function createAI(settings, fetcher = fetch) {
  const provider = settings.ai?.provider || 'openai';
  if (provider === 'gemini') return createGemini(settings, fetcher);
  if (provider === 'openai') return {...createOpenAI(settings, fetcher), provider};
  throw new Error('Invalid AI_PROVIDER');
}
