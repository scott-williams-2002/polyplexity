# Perplexity-Style Chat Interface Design Specification

## 1. Overview
A high-fidelity, reasoning-based chat interface that mimics modern research assistants (e.g., Perplexity AI). The design prioritizes transparency in the AI's process by visually stacking **Sources** first, **Reasoning** second, and the **Final Answer** third.

## 2. Visual Style & Theme

### 2.1 Core Aesthetic
- **Minimalist & Clean**: High whitespace, subtle borders, and a focus on typography.
- **Glassmorphism**: The input area uses `backdrop-blur-md` and semi-transparent backgrounds to float above the content.
- **Roundness**: 
  - Containers: `rounded-xl` (12px)
  - Message Bubbles: `rounded-2xl` (16px)
  - Buttons: `rounded-full`
- **Motion**: 
  - Smooth height transitions for the reasoning accordion.
  - Staggered fade-ins for source cards.
  - Pulsing animations for active states.

### 2.2 Color Palette (CSS Variables)
The theme relies on `hsl` values for seamless dark mode support.
- **Primary**: Teal/Cyan hue (`180 100% 25%`) used for accents and active states.
- **Muted**: Light grays (`240 4.8% 95.9%`) for backgrounds and secondary text.
- **Border**: Subtle borders (`240 5.9% 90%`) to define structure without visual weight.

---

## 3. Component Hierarchy & Visuals

The application is composed of a Sidebar (optional/collapsible) and a Main Chat Area. The Main Chat Area contains the scrolling message list and the sticky input area.

### 3.1 The Message Bubble (The Core Component)
This component is the heart of the "Reasoning" UI. It stacks content vertically in a specific chronological order of generation.

**Visual Stack:**
1.  **Sources Grid** (Top):
    - **Layout**: A grid of small cards (`h-24`).
    - **Appearance**: Each card shows the domain (tiny, muted) and title (truncated).
    - **Interaction**: Hovering a card changes the background (`bg-muted/50`) and highlights the text.
    - **Loading State**: If searching, a dashed border skeleton pulses.
    
2.  **Reasoning Accordion** (Middle):
    - **State**: Default **OPEN** while generating, auto-collapses to **CLOSED** when the final answer starts.
    - **Header**: A full-width clickable row. Contains a `BrainCircuit` icon (pulses when active), label "Thought Process", and a `ChevronDown`.
    - **Body**: An expandable panel with a gray left border (`border-l-2`). Text is `text-muted-foreground` (gray text) to differentiate it from the final answer.
    
3.  **Final Answer** (Bottom):
    - **Typography**: Standard markdown rendering (`prose`). High contrast text.
    - **Streaming**: Text appears character-by-character.
    
4.  **Action Footer**:
    - Appears only after generation is complete.
    - Contains small, ghost-style buttons for Copy, Rewrite, and Feedback.

### 3.2 Input Area
- **Positioning**: Sticky at the bottom (`fixed bottom-0`).
- **Visuals**: 
  - A distinct container with a border and shadow floats above the blurred background.
  - Inside, the textarea is borderless (`ring-0`) to look seamless.
- **Tools**: Small "pill" buttons (Focus, Attach) sit inside the input container, keeping the interface contained.

---

## 4. Interaction Events & Logic

### 4.1 The Streaming Lifecycle
The UI reacts to specific "Stages" of the AI generation to create a dynamic storytelling effect.

1.  **Stage: Searching**
    - **UI**: The Message Bubble appears. The **Sources Grid** is visible.
    - **Animation**: Source cards pop in one by one. A "Searching..." skeleton pulsates if no sources are found yet.
    
2.  **Stage: Reasoning**
    - **UI**: The **Reasoning Accordion** appears below the sources.
    - **State**: It is force-opened (`isOpen={true}`).
    - **Animation**: The text streams inside. The `BrainCircuit` icon in the header pulses. The container auto-scrolls to keep the newest thought visible.

3.  **Stage: Answering**
    - **UI**: The **Final Answer** text begins appearing below the accordion.
    - **Event**: Crucially, the Reasoning Accordion **automatically collapses** (`isOpen={false}`) to reduce vertical noise and focus the user on the answer.
    - **User Override**: The user can manually click the header to re-open the reasoning at any time.

4.  **Stage: Completed**
    - **UI**: The **Action Footer** fades in. All animations stop.

---

## 5. Reference Implementation

Below is the code structure for the `MessageBubble` which implements the layout and event logic described above.

```tsx
// components/MessageBubble.tsx

import React, { useEffect, useState } from 'react';
import { SourcesGrid } from './SourcesGrid';
import { ReasoningAccordion } from './ReasoningAccordion';
import { cn } from '../../lib/utils';
import ReactMarkdown from 'react-markdown';
import { Copy, RefreshCw, ThumbsUp, ThumbsDown } from './ui/Icons';

export const MessageBubble = ({ message, isLast }) => {
  const isUser = message.role === 'user';
  
  // LOGIC: Auto-collapse reasoning when answer starts streaming
  const [isReasoningOpen, setIsReasoningOpen] = useState(true);

  useEffect(() => {
    // Collapse when moving to 'answering' or 'completed'
    if (message.stage === 'answering' || message.stage === 'completed') {
      setIsReasoningOpen(false);
    }
    // Re-open if we go back to reasoning (rare, but good for state sync)
    if (message.stage === 'reasoning') {
      setIsReasoningOpen(true);
    }
  }, [message.stage]);

  // RENDER: User Message
  if (isUser) {
    return (
      <div className="flex justify-end mb-8">
        <div className="bg-muted/50 text-foreground px-5 py-3 rounded-2xl max-w-[80%] text-lg">
          {message.content}
        </div>
      </div>
    );
  }

  // RENDER: AI Message (The Stack)
  return (
    <div className="flex flex-col gap-2 mb-10 w-full max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* 1. SOURCES (Top) */}
      {message.sources && message.sources.length > 0 && (
        <SourcesGrid 
          sources={message.sources} 
          isStreaming={message.stage === 'searching'} 
        />
      )}

      {/* 2. REASONING (Middle) */}
      {message.reasoning && (
        <ReasoningAccordion 
          reasoning={message.reasoning} 
          isOpen={isReasoningOpen}
          isStreaming={message.stage === 'reasoning'}
          onToggle={() => setIsReasoningOpen(!isReasoningOpen)}
        />
      )}

      {/* 3. ANSWER CONTENT (Bottom) */}
      <div className="relative group">
        {!message.content && message.stage !== 'completed' && message.stage !== 'answering' ? (
             // Loading dots if waiting for answer generation to start
             <div className="flex items-center gap-2 text-muted-foreground py-4">
                <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce delay-75"></span>
                <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce delay-150"></span>
             </div>
        ) : (
          <div className="prose prose-neutral dark:prose-invert max-w-none text-foreground leading-relaxed">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* 4. FOOTER ACTIONS */}
      {(message.content || message.stage === 'completed') && (
        <div className="flex items-center gap-2 mt-4 pt-2">
          <ActionButton icon={<Copy />} label="Copy" />
          <ActionButton icon={<RefreshCw />} label="Rewrite" />
          <div className="flex-grow" />
          <ActionButton icon={<ThumbsUp />} />
          <ActionButton icon={<ThumbsDown />} />
        </div>
      )}
    </div>
  );
};
```
