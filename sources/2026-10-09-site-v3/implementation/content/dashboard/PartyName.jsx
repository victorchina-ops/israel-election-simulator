import React from "react";
import logo_beyachad from "../assets/party-logos/beyachad.png";
import logo_democrats from "../assets/party-logos/democrats.png";
import logo_joint from "../assets/party-logos/joint.png";
import logo_utj from "../assets/party-logos/utj.png";
import logo_yashar from "../assets/party-logos/yashar.png";
import logo_yisrael_beiteinu from "../assets/party-logos/yisrael_beiteinu.png";
import logo_gantz from "../assets/party-logos/gantz.png";
import logo_likud from "../assets/party-logos/likud.png";
import logo_otzma from "../assets/party-logos/otzma.png";
import logo_hendel from "../assets/party-logos/hendel.png";
import logo_winter from "../assets/party-logos/winter.png";
import logo_rz_zehut from "../assets/party-logos/rz_zehut.png";
import logo_raam from "../assets/party-logos/raam.png";
import logo_shas from "../assets/party-logos/shas.png";
import logo_noam from "../assets/party-logos/noam.png";
import logo_israel_first from "../assets/party-logos/israel_first.png";
import logo_haredi_public from "../assets/party-logos/haredi_public.svg";
import "./party-name.css";
const logos={haredi_public:logo_haredi_public,israel_first:logo_israel_first,noam:logo_noam,beyachad:logo_beyachad,democrats:logo_democrats,joint:logo_joint,utj:logo_utj,yashar:logo_yashar,yisrael_beiteinu:logo_yisrael_beiteinu,gantz:logo_gantz,likud:logo_likud,otzma:logo_otzma,hendel:logo_hendel,winter:logo_winter,rz_zehut:logo_rz_zehut,raam:logo_raam,shas:logo_shas};
export const PARTY_LOGOS=logos;
export const PARTY_COLORS={a:"#dc454c",b:"#2378cf",other:"#87909d",arab:"#87909d"};
export function PartyLogo({party}){
 if(!party||!logos[party.id])return null;
 return <img className={"party-logo"+(party.id==="israel_first"?" party-logo--dark":"")} src={logos[party.id]} alt="" width="76" height="30" loading="lazy"/>;
}
export function PartyName({party,bloc,showLogo=true,compact=false}){
 if(!party)return null;
 const group=bloc||party.bloc||party.defaultBloc||"other";
 return <span className={"party-name"+(compact?" party-name--compact":"")} title={compact?party.name:undefined} data-party-id={party.id} data-party-bloc={group} style={{color:PARTY_COLORS[group]||PARTY_COLORS.other}}>
  {showLogo&&<PartyLogo party={party}/>}
  <span>{party.name}</span>
 </span>;
}
export function PartyLogoSources(){return <p className="party-logo-source">סמלי הרשימות לפי <a href="https://electionsvote.mako.co.il/" target="_blank" rel="noreferrer">מצפן הבחירות 2026 של mako</a>. וכן האתרים הרשמיים של <a href="https://www.noamlisrael.org.il/" target="_blank" rel="noreferrer">נעם לישראל</a>, <a href="https://israelfirst.co.il/" target="_blank" rel="noreferrer">ישראל תחילה</a> ו<a href="https://hatzibur-haharedi.org/" target="_blank" rel="noreferrer">הציבור החרדי</a>. צבע השם מציין את הגוש; הסמלים מוצגים בצבעי המקור. סמלי התנועות אינם מצביעים על הרכב ממשלה מוסכם.</p>;}
