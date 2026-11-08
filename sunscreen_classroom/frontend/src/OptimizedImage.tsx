import {useState} from 'react';
import type {ImgHTMLAttributes} from 'react';

type Props = ImgHTMLAttributes<HTMLImageElement> & {src:string;fallbackSrc?:string};

export function OptimizedImage(props:Props){return <ImageSource key={props.src} {...props}/>;}

function ImageSource({src,fallbackSrc,...props}:Props){
 const [failed,setFailed]=useState(false);
 return <img decoding="async" {...props} src={failed&&fallbackSrc?fallbackSrc:src}
  onError={()=>{if(!failed&&fallbackSrc)setFailed(true);}}/>;
}
