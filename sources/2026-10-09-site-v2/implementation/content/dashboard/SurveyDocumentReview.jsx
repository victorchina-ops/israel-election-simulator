import React,{useMemo} from 'react';
import {DataComponent,Button,useDataApp} from '../../data-app-public.jsx';
import {dateLabel,downloadRows} from './transparency-data.js';
import './survey-document-review.css';

const statusLabel=report=>report.statusLabel||(report.includedInCurrentModel?'השלמת סקר קיים':'ארכיון — לא נכלל בשקלול');
const formatNumber=new Intl.NumberFormat('he-IL',{maximumFractionDigits:6});
function sourceLink(value){
 try{const url=new URL(value);return ['https:','http:'].includes(url.protocol)?url.href:null;}catch{return null;}
}
function cellLabel(value,column){
 if(value==null||value==='')return '—';
 if(typeof value!=='number')return String(value);
 if(!Number.isFinite(value))return '—';
 const percent=column.type==='percent'||(!column.type&&column.key.endsWith('Pct'));
 return formatNumber.format(value)+(percent?'%':'');
}

export function SurveyDocumentReview({review}){
 const {queries}=useDataApp();
 const reports=review?.reports??[];
 const rows=useMemo(()=>reports.flatMap(report=>(report.tables??[]).flatMap(table=>(table.rows??[]).map(row=>({
  documentId:report.id,fileName:report.fileName,publisher:report.publisher,pollster:report.pollster,
  date:report.date,status:statusLabel(report),includedInCurrentModel:report.includedInCurrentModel,
  table:table.label,sourcePage:table.page,sourceUrl:report.sourceUrl,...row
 })))),[reports]);
 if(!reports.length)return null;
 return <section className="survey-document-review" dir="rtl" data-survey-document-review>
  <DataComponent id="source-survey-documents" title="הדוחות שנבדקו בעדכון האחרון" variant="card" kind="table"
   queryId="survey_documents" sourceRows={queries.survey_documents?.rows??[]} displayRows={rows}
   description="טבלאות המקור שנבדקו, עם תאריך, מדגם ומעמד בשקלול. נתונים מתרחישים חלופיים או מסקרים ישנים מוצגים לעיון לפי הסימון בכל דוח.">
   <div className="sdr-toolbar"><p>נבדקו בתאריך <strong><bdi>{dateLabel(review.checkedAt)}</bdi></strong></p>
    <Button onClick={()=>downloadRows('reviewed-survey-documents-'+(review.checkedAt??'undated')+'.csv',rows)}>הורדת טבלאות הדוחות CSV</Button>
   </div>
   {review.summary&&<p className="sdr-intro">{review.summary}</p>}
   <div className="sdr-reports">{reports.map(report=>{
    const href=sourceLink(report.sourceUrl);
    return <details className="sdr-report" key={report.id} data-survey-document={report.id}>
     <summary><span className="sdr-report-title"><strong>{report.publisher}</strong><span><bdi>{dateLabel(report.date)}</bdi> · מדגם: <bdi>{report.sampleSize==null?'לא צוין':formatNumber.format(report.sampleSize)}</bdi></span></span>
      <span className={'sdr-status '+(report.includedInCurrentModel?'sdr-current':'sdr-archive')}>{statusLabel(report)}</span>
     </summary>
     <div className="sdr-report-content">
      <p className="sdr-source"><span>{report.pollster}</span>{href&&<a href={href} target="_blank" rel="noopener noreferrer">{report.sourceKind==='image'?'פתיחת צילום המקור':'פתיחת דוח המקור PDF'} <bdi>{report.fileName}</bdi></a>}</p>
      {report.primarySourceUrl&&<p><a href={sourceLink(report.primarySourceUrl)} target="_blank" rel="noopener noreferrer">הפרסום המקורי ופרטי שיטת הסקר</a></p>}
      {report.summary&&<p>{report.summary}</p>}
      {(report.tables??[]).map((table,index)=><section className="sdr-source-table" key={table.label+'-'+index}>
       <h3>{table.label} <span>· עמוד <bdi>{table.page??'לא צוין'}</bdi></span></h3>
       {table.summary&&<p>{table.summary}</p>}
       <div className="sdr-scroll" tabIndex={0} role="region" aria-label={report.publisher+' — '+table.label+'; ניתן לגלול לרוחב'}>
        <table data-reviewed-rows><thead><tr>{table.columns.map(column=><th key={column.key} scope="col">{column.label}</th>)}</tr></thead>
         <tbody>{(table.rows??[]).map((row,rowIndex)=><tr key={String(row.party??rowIndex)+'-'+rowIndex}>{table.columns.map((column,columnIndex)=>{
          const content=column.type==='text'||column.key==='party'?cellLabel(row[column.key],column):<bdi>{cellLabel(row[column.key],column)}</bdi>;
          return columnIndex===0?<th key={column.key} scope="row">{content}</th>:<td key={column.key}>{content}</td>;
         })}</tr>)}</tbody>
        </table>
       </div>
      </section>)}
     </div>
    </details>;
   })}</div>
  </DataComponent>
 </section>;
}
