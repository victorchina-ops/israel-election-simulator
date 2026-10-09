import React,{useState} from "react";
import {DataComponent,Dropdown,useDataApp} from "../../data-app-public.jsx";
import {PartyName} from "./PartyName.jsx";
import {reportedSupport} from "./transparency-data.js";
export function PollViewer({input,config}){
 const {queries}=useDataApp();
 const [open,setOpen]=useState(false),[selected,setSelected]=useState(input.current.polls[0]?.id);
 const poll=input.current.polls.find(p=>p.id===selected)||input.current.polls[0];
 if(!poll)return null;
 const rows=input.parties.filter(p=>p.ballot!==false).map(p=>({id:p.id,מפלגה:p.name,מנדטים:poll.seats?.[p.id]??null,"קולות (%)":reportedSupport(poll,p.id).value,סקר:poll.id,מקור:poll.sourceUrl}));
 return <details className="e-poll-detail" onToggle={e=>setOpen(e.currentTarget.open)}><summary>הסקרים המקוריים — פתיחת סקר בנפרד</summary>
 {open&&<DataComponent id="individual-poll-source" title="הנתונים שפורסמו בסקר הנבחר" variant="card" kind="table" queryId="polls" sourceRows={queries.polls.rows} displayRows={rows}>
  <Dropdown triggerClassName="filter-trigger e-content-select" contentClassName="election-select-menu" label="הסקר להצגה" showLabel value={poll.id} choices={input.current.polls.map(p=>p.id)} choiceLabels={Object.fromEntries(input.current.polls.map(p=>[p.id,p.publisher+" · "+p.date]))} onChange={setSelected}/>
  <p>{poll.pollster} · {poll.date} · מדגם {poll.sampleSize??"לא פורסם"} · <a href={poll.sourceUrl} target="_blank" rel="noreferrer">מקור הסקר</a></p>
  <p className="e-caption">אלה המנדטים ואחוזי התמיכה שפורסמו. מקף מציין נתון חסר; אחוזים חסרים לא שוחזרו בטבלה זו. בחירת הסקר כאן אינה משנה את המדד המשוקלל.</p>
  <div className="e-scroll"><table data-reviewed-rows><thead><tr><th>מפלגה</th><th>מנדטים שפורסמו</th><th>תמיכה שפורסמה</th></tr></thead><tbody>{rows.map(row=><tr key={row.id}><th><PartyName party={input.parties.find(p=>p.id===row.id)} bloc={config.partyBlocs[row.id]}/></th><td>{row.מנדטים??"—"}</td><td>{row["קולות (%)"]==null?"—":row["קולות (%)"]+"%"}</td></tr>)}</tbody></table></div>
 </DataComponent>}
 </details>;
}
