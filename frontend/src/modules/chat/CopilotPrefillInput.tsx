"use client";

import { takePendingChatPrefillForThread } from "@/lib/chatPrefillStorage";
import { useApp } from "@/providers/AppContext";
import { usePathname } from "next/navigation";
import { useChatContext } from "@copilotkit/react-ui";
import type { InputProps } from "@copilotkit/react-ui";
import { useCopilotChatInternal, useCopilotContext } from "@copilotkit/react-core";
import React, { useLayoutEffect, useMemo, useRef, useState } from "react";

const MAX_NEWLINES = 6;

/**
 * Same behavior as CopilotKit default chat input, plus one-shot composer text
 * stashed for the active thread (see ``stashChatComposerPrefillForThread``).
 */
export function CopilotPrefillInput({
  inProgress,
  onSend,
  chatReady = false,
  onStop,
  onUpload,
  hideStopButton = false,
}: InputProps) {
  const pathname = usePathname();
  const { effectiveThreadId } = useApp();
  const context = useChatContext();
  const copilotContext = useCopilotContext();

  const showPoweredBy = !copilotContext.copilotApiConfig?.publicApiKey;

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isComposing, setIsComposing] = useState(false);

  const [text, setText] = useState("");

  useLayoutEffect(() => {
    if (pathname !== "/") return;
    const pre = takePendingChatPrefillForThread(effectiveThreadId);
    if (pre != null && pre.length > 0) {
      queueMicrotask(() => setText(pre));
    }
  }, [pathname, effectiveThreadId]);

  const handleDivClick = (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    if (target.closest("button")) return;
    if (target.tagName === "TEXTAREA") return;
    textareaRef.current?.focus();
  };

  const send = () => {
    if (inProgress) return;
    void onSend(text);
    setText("");
    textareaRef.current?.focus();
  };

  const isInProgress = inProgress;
  const { buttonIcon, buttonAlt } = useMemo(() => {
    if (!chatReady)
      return { buttonIcon: context.icons.spinnerIcon, buttonAlt: "Loading" };
    return isInProgress && !hideStopButton && chatReady
      ? { buttonIcon: context.icons.stopIcon, buttonAlt: "Stop" }
      : { buttonIcon: context.icons.sendIcon, buttonAlt: "Send" };
  }, [
    isInProgress,
    chatReady,
    hideStopButton,
    context.icons.spinnerIcon,
    context.icons.stopIcon,
    context.icons.sendIcon,
  ]);

  const { interrupt } = useCopilotChatInternal();

  const canSend = useMemo(() => {
    return !isInProgress && text.trim().length > 0 && !interrupt;
  }, [interrupt, isInProgress, text]);

  const canStop = useMemo(() => {
    return isInProgress && !hideStopButton;
  }, [isInProgress, hideStopButton]);

  const sendDisabled = !canSend && !canStop;

  return (
    <div
      className={`copilotKitInputContainer ${showPoweredBy ? "poweredByContainer" : ""}`}
    >
      <div className="copilotKitInput" onClick={handleDivClick}>
        <textarea
          ref={textareaRef}
          className="copilotKitInput textarea"
          placeholder={context.labels.placeholder}
          rows={Math.min(MAX_NEWLINES, 4)}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !isComposing) {
              event.preventDefault();
              if (canSend) send();
            }
          }}
          style={{ overflow: "auto", resize: "none", width: "100%" }}
        />
        <div className="copilotKitInputControls">
          {onUpload && (
            <button type="button" onClick={onUpload} className="copilotKitInputControlButton">
              {context.icons.uploadIcon}
            </button>
          )}
          <div style={{ flexGrow: 1 }} />
          <button
            type="button"
            disabled={sendDisabled}
            onClick={isInProgress && !hideStopButton && onStop ? onStop : send}
            data-copilotkit-in-progress={inProgress}
            data-test-id={
              inProgress ? "copilot-chat-request-in-progress" : "copilot-chat-ready"
            }
            className="copilotKitInputControlButton"
            aria-label={buttonAlt}
          >
            {buttonIcon}
          </button>
        </div>
      </div>
      {showPoweredBy && (
        <p
          className="poweredBy"
          style={{
            visibility: "visible",
            display: "block",
            textAlign: "center",
            fontSize: "12px",
            padding: "3px 0",
            color: "rgb(214, 214, 214)",
          }}
        >
          Powered by CopilotKit
        </p>
      )}
    </div>
  );
}
