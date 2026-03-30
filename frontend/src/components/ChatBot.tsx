import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send, Bot, Loader2, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useDiagnosisContext } from "@/contexts/DiagnosisContext";

type Message = {
  role: "user" | "assistant";
  content: string;
  suggested_questions?: string[];
  disclaimer?: string;
};

const ChatBot = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello! I'm MediAI Assistant. I can help answer general health questions. How can I help you today?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false); // ✅ Request lock flag
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { activeDiagnosis } = useDiagnosisContext();

  // Generate session_id on first open
  useEffect(() => {
    if (open && !sessionId) {
      setSessionId(crypto.randomUUID());
    }
  }, [open, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    
    // ✅ PREVENT DUPLICATE REQUESTS - Check if already sending
    if (!messageText || loading || isSending) {
      if (isSending) {
        console.log("🚫 Request blocked (already sending)");
      }
      return;
    }

    // ✅ Set request lock IMMEDIATELY
    console.log("📤 Sending request...");
    setIsSending(true);
    
    const userMsg: Message = { role: "user", content: messageText };
    setMessages((p) => [...p, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.chat({
        message: messageText,
        session_id: sessionId!,
        diagnosis_context: activeDiagnosis,
      });
      console.log("✅ Chat response received:", res);
      if (res.session_id) setSessionId(res.session_id);
      setMessages((p) => [
        ...p,
        {
          role: "assistant",
          content: res.reply,
          suggested_questions: res.suggested_questions,
          disclaimer: res.disclaimer,
        },
      ]);
    } catch (error) {
      console.error("❌ Chat error:", error);
      setMessages((p) => [
        ...p,
        {
          role: "assistant",
          content: "I'm sorry, I couldn't connect to the server. Please note that I provide general health information only and this should not replace professional medical advice.",
        },
      ]);
    } finally {
      setLoading(false);
      setIsSending(false); // ✅ Release request lock
      console.log("✅ Request completed, lock released");
    }
  };

  const handleClear = async () => {
    if (sessionId) {
      try { await api.clearChat(sessionId); } catch { /* ignore */ }
    }
    setSessionId(crypto.randomUUID());
    setMessages([
      { role: "assistant", content: "Hello! I'm MediAI Assistant. How can I help you today?" },
    ]);
  };

  return (
    <>
      <motion.button
        onClick={() => setOpen(true)}
        className={`fixed bottom-6 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg btn-primary-gradient ${open ? "hidden" : ""}`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
      >
        <MessageCircle className="h-6 w-6" />
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-6 right-6 z-50 flex h-[500px] w-[380px] max-w-[calc(100vw-3rem)] flex-col overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border bg-primary px-5 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-foreground/20">
                  <Bot className="h-4 w-4 text-primary-foreground" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-primary-foreground">MediAI Assistant</p>
                  <p className="text-xs text-primary-foreground/70">
                    {activeDiagnosis ? `Context: ${activeDiagnosis.disease}` : "Online"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button onClick={handleClear} className="rounded-lg p-1 text-primary-foreground/70 hover:text-primary-foreground" title="Clear chat">
                  <Trash2 className="h-4 w-4" />
                </button>
                <button onClick={() => setOpen(false)} className="rounded-lg p-1 text-primary-foreground/70 hover:text-primary-foreground">
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Disclaimer */}
            <div className="border-b border-border bg-accent/10 px-4 py-2">
              <p className="text-xs text-accent-foreground">⚠️ This AI provides general info only. Not a substitute for professional medical advice.</p>
            </div>

            {/* Messages */}
            <div className="flex-1 space-y-3 overflow-y-auto p-4">
              {messages.map((m, i) => (
                <div key={i}>
                  <div className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                        m.role === "user"
                          ? "bg-primary text-primary-foreground rounded-br-md"
                          : "bg-muted text-foreground rounded-bl-md"
                      }`}
                    >
                      {m.content}
                    </div>
                  </div>
                  {/* Per-message disclaimer */}
                  {m.role === "assistant" && m.disclaimer && (
                    <p className="mt-1 ml-1 text-[10px] text-muted-foreground/60 italic">{m.disclaimer}</p>
                  )}
                  {/* Suggested questions chips */}
                  {m.role === "assistant" && m.suggested_questions && m.suggested_questions.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {m.suggested_questions.map((q, qi) => (
                        <button
                          key={qi}
                          onClick={() => {
                            console.log("💡 Suggested question clicked:", q);
                            handleSend(q);
                          }}
                          disabled={loading || isSending}
                          className="rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-foreground transition-colors hover:bg-primary/10 hover:text-primary hover:border-primary/40 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 rounded-2xl bg-muted px-4 py-2.5 text-sm text-muted-foreground rounded-bl-md">
                    <Loader2 className="h-3 w-3 animate-spin" /> Thinking...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t border-border p-3">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    // ✅ Only trigger on Enter WITHOUT Shift (allow Shift+Enter for newlines)
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault(); // ✅ Prevent default form submission
                      console.log("↩️ Enter key pressed, calling handleSend");
                      handleSend();
                    }
                  }}
                  placeholder="Type a message..."
                  disabled={loading || isSending}
                  className="flex-1 rounded-xl border border-border bg-muted px-4 py-2.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary/30 disabled:opacity-50"
                />
                <button 
                  onClick={() => {
                    console.log("🖱️ Send button clicked");
                    handleSend();
                  }}
                  disabled={loading || isSending} 
                  className="btn-primary-gradient rounded-xl px-3 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatBot;
