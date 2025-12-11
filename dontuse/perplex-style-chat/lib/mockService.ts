import { ReferenceSource, Message, StreamStage } from '../types';
import { generateId, delay } from './utils';

// Mock data to simulate a complex query response
const MOCK_SOURCES: ReferenceSource[] = [
  { id: '1', title: 'React Documentation', url: 'https://react.dev', domain: 'react.dev' },
  { id: '2', title: 'Tailwind CSS', url: 'https://tailwindcss.com', domain: 'tailwindcss.com' },
  { id: '3', title: 'MDN Web Docs', url: 'https://developer.mozilla.org', domain: 'developer.mozilla.org' },
  { id: '4', title: 'Stack Overflow Discussion', url: 'https://stackoverflow.com', domain: 'stackoverflow.com' },
];

const MOCK_REASONING_STEPS = [
  "Analyzing the user's request for a chat interface...",
  "Identifying key requirements: shadcn style, streaming, reasoning traces, and collapsible sources.",
  "Searching for design patterns similar to Perplexity AI.",
  "Structuring the component hierarchy: MessageBubble, SourceGrid, ReasoningAccordion.",
  "Determining the state management strategy for streaming phases.",
  "Drafting the response with code examples and explanations."
];

const MOCK_FINAL_ANSWER = `
Based on your request, I've designed a **high-fidelity chat interface** that mirrors the aesthetic and functionality of modern research assistants like Perplexity.

### Key Features Implemented:
1.  **Multi-Stage Streaming:** The interface handles 'Searching', 'Reasoning', and 'Answering' states distinctively.
2.  **Reasoning Trace:** A collapsible "Thinking" section that expands during generation and collapses automatically when finished.
3.  **Source Citations:** A horizontal scrollable grid of sources that appears before the final answer.
4.  **Clean Aesthetics:** Utilizing a minimal grayscale palette with precise border radii and typography.

You can try typing another query to see the animation sequence again!
`;

/**
 * Simulates a streaming response. 
 * This generator yields updates to the message state.
 */
export async function* mockStreamResponse(userQuery: string): AsyncGenerator<Partial<Message>> {
  
  // 1. Searching Phase
  yield { stage: 'searching', isStreaming: true, content: '' };
  await delay(800);
  
  // Simulate finding sources one by one
  const sources: ReferenceSource[] = [];
  for (const source of MOCK_SOURCES) {
    sources.push(source);
    yield { sources: [...sources] }; // Update sources
    await delay(300);
  }
  
  await delay(500);

  // 2. Reasoning Phase
  yield { stage: 'reasoning', sources };
  let currentReasoning = "";
  
  for (const step of MOCK_REASONING_STEPS) {
    // Simulate typing the reasoning step
    const prefix = currentReasoning ? "\n\n" : "";
    const newStep = `> ${step}`;
    
    // Type out the step character by character (fast)
    for (let i = 0; i < newStep.length; i++) {
       currentReasoning += newStep[i];
       if (i % 3 === 0) yield { reasoning: currentReasoning }; // Batch updates slightly
       await delay(10);
    }
    currentReasoning += prefix;
    yield { reasoning: currentReasoning };
    await delay(400); // Pause between thought steps
  }

  await delay(600);

  // 3. Answering Phase
  yield { stage: 'answering' };
  
  let currentContent = "";
  const words = MOCK_FINAL_ANSWER.split(" ");
  
  for (const word of words) {
    currentContent += word + " ";
    yield { content: currentContent };
    // Variable delay to simulate natural token generation
    await delay(Math.random() * 30 + 20); 
  }

  // 4. Completion
  yield { stage: 'completed', isStreaming: false };
}