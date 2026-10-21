import { useEffect, useState } from 'react';
import type Keycloak from 'keycloak-js';
type Doc={id:number;filename:string;status:string;error:string;byte_size:number;chunk_count:number;embedding_model:string};
type Source={document_id:number;filename:string;page:number|null;chunk_index:number;similarity:number;excerpt:string};
type Msg={id:number;role:'user'|'assistant';content:string;sources:Source[];model:string};
type Conversation={id:number;title:string;updated_at:string};
const API='http://localhost:8200';
export default function App({keycloak}:{keycloak:Keycloak}) {
  const [docs,setDocs]=useState<Doc[]>([]);
  const [file,setFile]=useState<File|null>(null);
  const [query,setQuery]=useState('');
  const [question,setQuestion]=useState('');
  const [results,setResults]=useState<{filename:string;text:string;similarity:number;page:number|null}[]>([]);
  const [conversations,setConversations]=useState<Conversation[]>([]);
  const [activeId,setActiveId]=useState<number|null>(null);
  const [messages,setMessages]=useState<Msg[]>([]);
  const [busy,setBusy]=useState(false);
  const [streamText,setStreamText]=useState('');
  const [streamStatus,setStreamStatus]=useState('');
  const [streamSources,setStreamSources]=useState<Source[]>([]);
  const [pendingQuestion,setPendingQuestion]=useState('');
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [provider,setProvider]=useState<'ollama'|'openai'>('ollama');
  const [mode,setMode]=useState<'auto'|'rag'|'agent'>('auto');
  const [toolStatus,setToolStatus]=useState('');
  const [tab,setTab]=useState<'chat'|'documents'>('chat');
  async function api(path:string,options:RequestInit={}) {
    await keycloak.updateToken(30);
    const headers=new Headers(options.headers);
    headers.set('Authorization',`Bearer ${keycloak.token}`);
    const response=await fetch(API+path,{...options,headers});
    if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(`${response.status}: ${typeof body.detail==='string'?body.detail:JSON.stringify(body.detail??body)}`);}
    return response.status===204?null:response.json();
  }
  async function refresh(){
    const [list,chats]=await Promise.all([api('/api/knowledge/documents/'),api('/api/chat/conversations/')]);
    setDocs(list.documents);setConversations(chats.conversations);
  }
  useEffect(()=>{void refresh().catch(e=>setError(String(e)));},[]);
  async function selectConversation(id:number){
    setError('');setActiveId(id);setMessages([]);setStreamText('');setPendingQuestion('');
    try{const result=await api(`/api/chat/conversations/${id}/`);setMessages(result.messages);}catch(e){setError(String(e));}
  }
   async function send(){
     if(busy||question.trim().length<2)return;
     const text=question.trim();setBusy(true);setError('');setNotice('');
     setPendingQuestion(text);setStreamText('');setStreamSources([]);setStreamStatus('Connecting...');setToolStatus('');setQuestion('');
     let completed=false;
     try{
       await keycloak.updateToken(30);
       const response=await fetch(API+'/api/chat/ask-stream/',{
         method:'POST',headers:{'Content-Type':'application/json','Accept':'text/event-stream','Authorization':`Bearer ${keycloak.token}`},
         body:JSON.stringify({question:text,conversation_id:activeId,provider,mode})
       });
       if(!response.ok){
         const body=await response.json().catch(()=>({}));
         throw new Error(`${response.status}: ${typeof body.detail==='string'?body.detail:JSON.stringify(body.detail??body)}`);
       }
       if(!response.body)throw new Error('Browser did not provide a streaming response');
       const reader=response.body.getReader();const decoder=new TextDecoder();let buffer='';
       const handleEvent=(frame:string)=>{
         let event='message';const dataLines:string[]=[];
         for(const line of frame.split('\n')){
           if(line.startsWith('event:'))event=line.slice(6).trim();
           if(line.startsWith('data:'))dataLines.push(line.slice(5).trimStart());
         }
         if(!dataLines.length)return;
         const payload=JSON.parse(dataLines.join('\n'));
         if(event==='status')setStreamStatus(payload.message||'Working...');
         if(event==='tool')setToolStatus(`${payload.name}: ${payload.status}`);
         if(event==='sources')setStreamSources(payload.sources||[]);
         if(event==='token')setStreamText(v=>v+(payload.text||''));
         if(event==='error')throw new Error(payload.detail||'Chat streaming failed');
         if(event==='done'){
           completed=true;
           setActiveId(payload.conversation.id);
           setMessages(v=>[...v,payload.user_message,payload.assistant_message]);
           setStreamText('');setStreamSources([]);setPendingQuestion('');setStreamStatus('');
         }
       };
       try{
         while(true){
           const {done,value}=await reader.read();if(done)break;
           buffer+=decoder.decode(value,{stream:true}).replace(/\r\n/g,'\n');
           let index;
           while((index=buffer.indexOf('\n\n'))!==-1){
             const frame=buffer.slice(0,index);buffer=buffer.slice(index+2);
             if(frame.trim())handleEvent(frame);
           }
         }
         buffer+=decoder.decode();
         if(buffer.trim())handleEvent(buffer);
       }finally{reader.releaseLock();}
       if(!completed)throw new Error('Connection closed before the answer was saved');
       const chats=await api('/api/chat/conversations/');setConversations(chats.conversations);
     }catch(e){setError(String(e));setQuestion(text);}
     finally{setBusy(false);setStreamStatus('');if(!completed){setStreamText('');setStreamSources([]);setPendingQuestion('');}}
   }
  async function upload(){if(!file||busy)return;setBusy(true);setError('');setNotice('Indexing document...');
    try{const form=new FormData();form.append('file',file);const result=await api('/api/knowledge/documents/',{method:'POST',body:form});
      setNotice(result.status==='ready'?`Indexed ${result.chunk_count} chunks`:`Indexing failed: ${result.error}`);setFile(null);
      const input=document.getElementById('doc-file') as HTMLInputElement|null;if(input)input.value='';await refresh();
    }catch(e){setError(String(e));setNotice('');}finally{setBusy(false);}}
  async function removeDoc(id:number){if(!window.confirm('Delete this document and its chunks?'))return;
    try{await api(`/api/knowledge/documents/${id}/`,{method:'DELETE'});await refresh();setResults([]);}catch(e){setError(String(e));}}
  async function removeChat(id:number){if(!window.confirm('Delete this conversation?'))return;
    try{await api(`/api/chat/conversations/${id}/`,{method:'DELETE'});if(activeId===id){setActiveId(null);setMessages([]);}await refresh();}catch(e){setError(String(e));}}
  async function search(){if(query.trim().length<2)return;setBusy(true);setError('');
    try{const result=await api('/api/knowledge/search/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query})});setResults(result.results);}catch(e){setError(String(e));}finally{setBusy(false);}}
  return <main>
    <header><h1>RAG Knowledge AI</h1><div className="action"><span className="muted">{keycloak.tokenParsed?.preferred_username}</span><button onClick={()=>keycloak.logout({redirectUri:'http://localhost:5174/'})}>Logout</button></div></header>
    <nav className="tabs"><button className={tab==='chat'?'selected':''} onClick={()=>setTab('chat')}>AI Chat</button><button className={tab==='documents'?'selected':''} onClick={()=>setTab('documents')}>Knowledge Base ({docs.length})</button></nav>
    {error&&<p className="error" role="alert">{error}</p>}{notice&&<p className="notice">{notice}</p>}
    {tab==='chat'?<div className="chat-layout"><aside className="sidebar"><div className="action"><h3>Conversations</h3><button onClick={()=>{setActiveId(null);setMessages([]);setStreamText('');setPendingQuestion('');setError('');}}>+ New</button></div>
      {conversations.map(c=><div className={`chat-row ${activeId===c.id?'active':''}`} key={c.id}><button className="chat-link" onClick={()=>void selectConversation(c.id)}>{c.title}</button><button className="delete-small" title="Delete conversation" onClick={()=>void removeChat(c.id)}>×</button></div>)}
      {!conversations.length&&<p className="muted">No previous conversations</p>}</aside>
      <section className="chat-panel"><h2>Phase 4 · RAG and Agent Chat</h2><div className="action"><label>Provider <select value={provider} disabled={busy} onChange={e=>setProvider(e.target.value as 'ollama'|'openai')}><option value="ollama">Ollama · Local</option><option value="openai">OpenAI · API</option></select></label><label>Mode <select value={mode} disabled={busy} onChange={e=>setMode(e.target.value as 'auto'|'rag'|'agent')}><option value="auto">Auto · Smart routing</option><option value="rag">Standard RAG</option><option value="agent">Agentic · Read-only</option></select></label></div><p className="muted">{mode==='auto'?'Auto chooses between general AI knowledge and your indexed documents. Web search is disabled; document citations appear when used.':mode==='rag'?'Answers use only authorized uploaded documents, with source citations.':'Agentic mode chooses a read-only tool: knowledge search or calculator.'}</p>
        <div className="message-list">{messages.length?messages.map(m=><div className={`message ${m.role}`} key={m.id}><div className="message-label">{m.role==='assistant'?'AI Assistant':'You'}{m.model&&<small> · {m.model}</small>}</div><p>{m.content}</p>{m.sources?.length>0&&<details><summary>Sources ({m.sources.length})</summary>{m.sources.map((s,i)=><div className="source" key={`${s.document_id}-${s.chunk_index}-${i}`}><strong>[{i+1}] {s.filename}</strong><small> · chunk {s.chunk_index}{s.page?` · page ${s.page}`:''} · similarity {s.similarity}</small><p>{s.excerpt}</p></div>)}</details>}</div>):!busy?<div className="chat-empty">Ask about your documents or request general AI help. For example: <em>Which technology handles authentication?</em></div>:null}{pendingQuestion&&<div className="message user"><div className="message-label">You</div><p>{pendingQuestion}</p></div>}{busy&&<div className="message assistant" aria-live="polite"><div className="message-label">AI Assistant · {streamStatus||'Working...'}</div><p>{streamText||'Please wait...'}{toolStatus&&<small> · Tool: {toolStatus}</small>}</p>{streamSources.length>0&&<details><summary>Sources ({streamSources.length})</summary>{streamSources.map((src,i)=><div className="source" key={i}><strong>[{i+1}] {src.filename}</strong><small> · chunk {src.chunk_index} · similarity {src.similarity}</small><p>{src.excerpt}</p></div>)}</details>}</div>}</div>
         <div className="chat-entry"><textarea aria-label="Your question" rows={3} value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();void send();}}} placeholder="Ask a general question or about your documents..."/><button disabled={busy||question.trim().length<2} onClick={()=>void send()}>{busy?'Streaming...':'Send'}</button></div>
      </section></div>:
      <section><h2>Phase 2 · Knowledge Base</h2><article><h3>Upload knowledge document</h3><p className="muted">Text-based PDF, DOCX, TXT or Markdown • max 10 MB</p><div className="action"><input id="doc-file" type="file" accept=".pdf,.docx,.txt,.md" onChange={e=>setFile(e.target.files?.[0]??null)}/><button disabled={!file||busy} onClick={()=>void upload()}>{busy?'Indexing...':'Upload & index'}</button></div></article>
      <article><h3>My documents ({docs.length})</h3>{docs.map(d=><div className="doc" key={d.id}><div><strong>{d.filename}</strong><p className="muted">{d.status} · {d.chunk_count} chunks · {d.embedding_model} · {(d.byte_size/1024).toFixed(1)} KB</p>{d.error&&<p className="error">{d.error}</p>}</div><button onClick={()=>void removeDoc(d.id)}>Delete</button></div>)}{docs.length===0&&<p className="muted">No indexed documents yet</p>}</article>
      <article><h3>Test semantic retrieval</h3><div className="action"><input className="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search document content"/><button disabled={busy||query.trim().length<2} onClick={()=>void search()}>Search</button></div>{results.map((m,i)=><div className="match" key={i}><strong>{m.filename}{m.page?` · p.${m.page}`:''}</strong><small>Similarity: {m.similarity}</small><p>{m.text}</p></div>)}</article></section>}
    <p className="muted">Local development · Keycloak-secured · RAG sources from your uploaded documents</p>
  </main>;
}
