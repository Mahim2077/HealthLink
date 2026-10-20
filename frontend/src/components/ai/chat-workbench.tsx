"use client";

import { PaperAirplaneIcon, Bars3BottomLeftIcon, ChatBubbleLeftRightIcon, CheckIcon, ChevronDownIcon, DocumentDuplicateIcon, DocumentTextIcon, HeartIcon, InformationCircleIcon, PlusIcon, ShieldCheckIcon, TrashIcon, XMarkIcon } from "@heroicons/react/24/outline";
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AiProcessingNotice, sourceCategoryLabels } from "./ai-context-notice";
import { deleteConversation, listConversations, loadConversation, sendConversationMessage } from "@/lib/ai/api";
import type { ChatMode, ConversationDetail, ConversationSendRequest, ConversationSummary, ConversationTurn } from "@/lib/ai/types";
import styles from "./chat-workbench.module.css";

const time = (value: string) => new Date(value).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
function group(value: string) {
  const now = new Date(); const date = new Date(value);
  if (date.toDateString() === now.toDateString()) return "Today";
  now.setDate(now.getDate() - 1);
  return date.toDateString() === now.toDateString() ? "Yesterday" : "Earlier";
}
const errorMessage = (reason: unknown) => reason instanceof Error ? reason.message : "Something went wrong. Please try again.";

export function ChatWorkbench({ symptomPanel }: { symptomPanel: ReactNode }) {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [nextOffset, setNextOffset] = useState<number | null>(null);
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [message, setMessage] = useState("");
  const [mode, setMode] = useState<ChatMode>("GENERAL");
  const [consented, setConsented] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [symptoms, setSymptoms] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<ConversationSummary | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const cancelDelete = useRef<HTMLButtonElement>(null);
  const abort = useRef<AbortController | null>(null);
  const alive = useRef(true);
  const retry = useRef<ConversationSendRequest | null>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const contextButton = useRef<HTMLButtonElement>(null);
  const id = useId();

  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    void listConversations(0, controller.signal).then(page => {
      setItems(previous => [...previous, ...page.items.filter(item => !previous.some(old => old.id === item.id))]); setNextOffset(page.next_offset); setHistoryLoading(false);
    }).catch(reason => { if (!controller.signal.aborted) { setHistoryError(errorMessage(reason)); setHistoryLoading(false); } });
    return () => { alive.current = false; controller.abort(); abort.current?.abort(); };
  }, []);
  useEffect(() => { scroll.current?.scrollTo?.({ top: scroll.current.scrollHeight, behavior: "instant" }); }, [conversation?.id, conversation?.turns.length, pendingQuestion]);
  useEffect(() => { if (deleting) cancelDelete.current?.focus(); }, [deleting]);

  function resetComposer() {
    setMessage(""); setError(""); setMode("GENERAL"); setConsented(false); setSettingsOpen(false); retry.current = null;
  }
  function startNew() {
    if (busy) return;
    setConversation(null); resetComposer(); setSymptoms(false); setHistoryOpen(false); setDeleting(null); input.current?.focus();
  }
  async function openConversation(item: ConversationSummary) {
    if (busy) return;
    setBusy(true); setError(""); setDeleting(null);
    const controller = new AbortController(); abort.current = controller;
    try {
      const detail = await loadConversation(item.id, controller.signal);
      if (!alive.current) return;
      setConversation(detail); resetComposer(); setSymptoms(false); setHistoryOpen(false);
    } catch (reason) { if (alive.current) setError(errorMessage(reason)); }
    finally { if (alive.current) setBusy(false); }
  }
  async function fetchHistory(offset = 0) {
    if (historyLoading) return;
    setHistoryLoading(true); setHistoryError("");
    const controller = new AbortController(); abort.current = controller;
    try {
      const page = await listConversations(offset, controller.signal);
      if (!alive.current) return;
      setItems(previous => offset ? [...previous, ...page.items.filter(item => !previous.some(old => old.id === item.id))] : page.items);
      setNextOffset(page.next_offset);
    } catch (reason) { if (alive.current) setHistoryError(errorMessage(reason)); }
    finally { if (alive.current) setHistoryLoading(false); }
  }
  async function removeConversation() {
    if (!deleting || busy) return;
    setBusy(true); setDeleteError("");
    try {
      await deleteConversation(deleting.id);
      if (!alive.current) return;
      setItems(previous => previous.filter(item => item.id !== deleting.id));
      setNextOffset(previous => previous === null ? null : Math.max(0, previous - 1));
      if (conversation?.id === deleting.id) { setConversation(null); resetComposer(); }
      setDeleting(null);
    } catch (reason) { if (alive.current) setDeleteError(errorMessage(reason)); }
    finally { if (alive.current) setBusy(false); }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = message.trim();
    if (busy || content.length < 3 || (mode === "RECORD_AWARE" && !consented)) return;
    const payload: ConversationSendRequest = retry.current ?? { conversation_id: conversation?.id ?? null, client_request_id: crypto.randomUUID(), message: content, mode, use_my_health_records: mode === "RECORD_AWARE" };
    retry.current = payload;
    setBusy(true); setPendingQuestion(content); setError(""); setConsented(false); setSettingsOpen(false);
    const controller = new AbortController(); abort.current = controller;
    try {
      const result = await sendConversationMessage(payload, controller.signal);
      if (!alive.current) return;
      setConversation(previous => ({ ...result.conversation, turns: [...(previous?.turns ?? []).filter(turn => turn.id !== result.turn.id), result.turn] }));
      if (!items.some(item => item.id === result.conversation.id)) setNextOffset(previous => previous === null ? null : previous + 1);
      setItems(previous => [result.conversation, ...previous.filter(item => item.id !== result.conversation.id)]);
      resetComposer();
    } catch (reason) { if (alive.current) { setError(errorMessage(reason)); if (mode === "RECORD_AWARE") setSettingsOpen(true); } }
    finally { if (alive.current) { setBusy(false); setPendingQuestion(""); input.current?.focus(); } }
  }
  function changeMode(value: ChatMode) {
    setMode(value); setConsented(false); setError(""); retry.current = null;
  }
  const turns = conversation?.turns ?? [];
  const hasRecordHistory = turns.some(turn => turn.mode === "RECORD_AWARE");

  return (
    <div className={styles.workspace}>
      <button type="button" className={styles.mobileHistory} aria-expanded={historyOpen} aria-controls={`${id}-history`} onClick={() => setHistoryOpen(value => !value)}><Bars3BottomLeftIcon aria-hidden="true" />Conversations<ChevronDownIcon aria-hidden="true" /></button>
      <aside id={`${id}-history`} aria-label="Conversation history" className={`${styles.sidebar} ${historyOpen ? styles.sidebarOpen : ""}`}>
        <h2>Conversations</h2>
        <button className={styles.newChat} disabled={busy} onClick={startNew} type="button"><PlusIcon aria-hidden="true" />New conversation</button>
        <div className={styles.historyList}>
          {(["Today", "Yesterday", "Earlier"] as const).map(label => {
            const entries = items.filter(item => group(item.updated_at) === label);
            return entries.length ? <section key={label} aria-label={label}><h3>{label}</h3>{entries.map(item => <div key={item.id} className={`${styles.historyItem} ${conversation?.id === item.id ? styles.selected : ""}`}>
              <button className={styles.historySelect} aria-current={conversation?.id === item.id ? "true" : undefined} disabled={busy} onClick={() => void openConversation(item)} type="button"><span>{item.title}</span><time dateTime={item.updated_at}>{label === "Earlier" ? new Date(item.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : time(item.updated_at)}</time></button>
              <button className={styles.deleteButton} aria-label={`Delete conversation: ${item.title}`} disabled={busy} onClick={() => { setDeleteError(""); setDeleting(item); setHistoryOpen(true); }} type="button"><TrashIcon aria-hidden="true" /></button>
            </div>)}</section> : null;
          })}
          {historyLoading ? <p className={styles.small} role="status">Loading conversations…</p> : null}
          {historyError ? <div className={styles.small} role="alert"><p>{historyError}</p><button className={styles.textButton} onClick={() => void fetchHistory()} type="button">Retry history</button></div> : null}
          {!items.length && !historyLoading && !historyError ? <p className={styles.small}>Your conversations will appear here after your first message.</p> : null}
          {nextOffset !== null ? <button className={styles.textButton} disabled={historyLoading || busy} onClick={() => void fetchHistory(nextOffset)} type="button">Load older conversations</button> : null}
        </div>
        {deleting ? <div className={styles.deleteConfirm} role="alertdialog" aria-labelledby={`${id}-delete-title`} aria-describedby={`${id}-delete-description`}><h3 id={`${id}-delete-title`}>Delete conversation?</h3><p id={`${id}-delete-description`}>“{deleting.title}” and its messages will be removed from your account. This cannot be undone.</p>{deleteError ? <p role="alert">{deleteError}</p> : null}<div><button ref={cancelDelete} type="button" disabled={busy} onClick={() => setDeleting(null)}>Cancel</button><button type="button" disabled={busy} onClick={() => void removeConversation()}>Delete permanently</button></div></div> : null}
        <p className={styles.privacy}><ShieldCheckIcon aria-hidden="true" />Saved privately to your account.<br />You can delete conversations here.</p>
      </aside>
      <section className={styles.chat} aria-label="HealthLink AI assistant">
        <header className={styles.header}><div><h1>AI assistant</h1><h2>{symptoms ? "Symptom guidance" : conversation?.title ?? "A little clarity for your health"}</h2><p>{symptoms ? "Conservative, non-diagnostic safety information" : conversation ? `Private conversation · ${new Date(conversation.created_at).toLocaleDateString()}` : "Understand medical information. Prepare for your next visit."}</p></div><button type="button" disabled={busy} className={styles.toolLink} onClick={() => { setSymptoms(value => !value); setHistoryOpen(false); }}><HeartIcon aria-hidden="true" />{symptoms ? "Back to chat" : "Symptom guidance"}</button></header>
        {symptoms ? <div className={styles.symptoms}>{symptomPanel}</div> : <>
          <div ref={scroll} className={styles.transcript} role="region" aria-label="Conversation messages" aria-live="polite" aria-relevant="additions" tabIndex={0}>
            {!turns.length && !pendingQuestion ? <div className={styles.empty}><span className={styles.avatar}><ChatBubbleLeftRightIcon aria-hidden="true" /></span><h2>What would you like to understand?</h2><p>Ask about a medical term, a test result, or what to discuss with your doctor. I can explain, but I cannot diagnose or prescribe.</p><div className={styles.starters}>{["What does a laboratory reference range mean?", "What should I ask my doctor about a medicine?", "How can I prepare for my next appointment?"].map(prompt => <button key={prompt} disabled={busy} onClick={() => { setMessage(prompt); setConsented(false); retry.current = null; input.current?.focus(); }} type="button">{prompt}</button>)}</div></div> : null}
            {turns.map(turn => <Turn key={turn.id} turn={turn} />)}
            {pendingQuestion ? <><div className={styles.userMessage}><p>{pendingQuestion}</p></div><p className={styles.loading} role="status">Preparing a careful response…</p></> : null}
          </div>
          <div className={styles.composerArea}>
            {error ? <p className={styles.error} role="alert">{error}{message ? " Your question is kept below; you can try again." : ""}</p> : null}
            <form className={styles.composer} onSubmit={submit}>
              <button ref={contextButton} className={styles.contextToggle} aria-expanded={settingsOpen} aria-controls={`${id}-context`} disabled={busy} type="button" onClick={() => setSettingsOpen(value => !value)}><DocumentTextIcon aria-hidden="true" />{mode === "GENERAL" ? "General · Records off" : consented ? "Records allowed · This request only" : "Use my records · Consent needed"}<ChevronDownIcon aria-hidden="true" /></button>
              {settingsOpen ? <div id={`${id}-context`} className={styles.contextPanel} onKeyDown={event => { if (event.key === "Escape") { setSettingsOpen(false); contextButton.current?.focus(); } }}>
                <div className={styles.contextHeading}><strong>Response context</strong><button aria-label="Close response context" type="button" onClick={() => { setSettingsOpen(false); contextButton.current?.focus(); }}><XMarkIcon aria-hidden="true" /></button></div>
                <fieldset disabled={busy}><legend className="sr-only">Response context</legend><label><input type="radio" name={`${id}-mode`} checked={mode === "GENERAL"} onChange={() => changeMode("GENERAL")} />General information</label><label><input type="radio" name={`${id}-mode`} checked={mode === "RECORD_AWARE"} onChange={() => changeMode("RECORD_AWARE")} />Use my records</label></fieldset>
                <AiProcessingNotice records={mode === "RECORD_AWARE"} />
                {mode === "RECORD_AWARE" ? <label className={styles.consent}><input type="checkbox" checked={consented} disabled={busy} onChange={event => setConsented(event.target.checked)} /><span>I allow HealthLink AI to use my personal medical records and this conversation for this request.</span></label> : null}
                {hasRecordHistory && mode === "GENERAL" ? <p className={styles.small}>To protect your records, General mode answers independently after a record-aware exchange. Allow records again for a record-aware follow-up.</p> : null}
                <p className={styles.small}>Questions and answers are saved privately until you delete the conversation. They are not clinical records.</p>
              </div> : null}
              <div className={styles.inputRow}><label className="sr-only" htmlFor={`${id}-question`}>Your question</label><textarea ref={input} id={`${id}-question`} disabled={busy} rows={2} minLength={3} maxLength={1500} required value={message} placeholder={turns.length ? "Ask a follow-up…" : "Ask a health question…"} onChange={event => { setMessage(event.target.value); setConsented(false); retry.current = null; setError(""); }} onKeyDown={event => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} /><button className={styles.send} type="submit" aria-label="Send message" disabled={busy || message.trim().length < 3 || (mode === "RECORD_AWARE" && !consented)}><PaperAirplaneIcon aria-hidden="true" /></button></div>
            </form>
            <p className={styles.footer}><InformationCircleIcon aria-hidden="true" />Educational support. Not a diagnosis or prescription.</p>
            <p className={styles.providerNote}>Questions are sent to the configured AI provider. Avoid identifying details. <span>{message.length}/1500</span></p>
          </div>
        </>}
      </section>
    </div>
  );
}

function Turn({ turn }: { turn: ConversationTurn }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText([turn.response.answer, ...turn.response.record_observations.map(item => `${item.statement} Source: ${sourceCategoryLabels(item.source_categories)}`), ...turn.response.questions_for_clinician, turn.response.disclaimer].join("\n\n"));
      setCopied(true); setCopyError(false);
    } catch { setCopyError(true); }
  }
  return <article className={styles.turn} aria-label="Question and answer"><div className={styles.userMessage}><p>{turn.message}</p><time dateTime={turn.created_at}>{time(turn.created_at)}{turn.mode === "RECORD_AWARE" ? " · Records allowed for this request" : ""}</time></div><div className={styles.assistantMessage}><span className={styles.avatar}><ChatBubbleLeftRightIcon aria-hidden="true" /></span><div><h3 className="sr-only">HealthLink AI response</h3><p className={styles.answer}>{turn.response.answer}</p>{turn.response.record_observations.length ? <div className={styles.observations}><h4>From your HealthLink records</h4>{turn.response.record_observations.map((item, index) => <p key={index}>{item.statement}<small>Source: {sourceCategoryLabels(item.source_categories)}</small></p>)}</div> : null}{turn.response.questions_for_clinician.length ? <div className={styles.questions}><h4>Questions for your clinician</h4><ul>{turn.response.questions_for_clinician.map(question => <li key={question}>{question}</li>)}</ul></div> : null}<div className={styles.messageActions}><time dateTime={turn.created_at}>{time(turn.created_at)}</time><button type="button" aria-label={copied ? "Response copied" : "Copy response"} onClick={() => void copy()}>{copied ? <CheckIcon aria-hidden="true" /> : <DocumentDuplicateIcon aria-hidden="true" />}</button><span role="status">{copyError ? "Could not copy. Select the text to copy it." : copied ? "Copied" : ""}</span></div><details className={styles.safety}><summary>Safety reminder</summary><p>{turn.response.disclaimer}</p></details></div></div></article>;
}
