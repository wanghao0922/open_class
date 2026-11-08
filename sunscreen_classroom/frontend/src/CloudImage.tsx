import {useState} from 'react';
import type {ImgHTMLAttributes} from 'react';
import type {Molecule} from './types';

type Props = Omit<ImgHTMLAttributes<HTMLImageElement>,'src'> & {molecule:Molecule};

export function CloudImage({molecule,...props}:Props){
 // Remount on source changes so a failed image cannot affect the next molecule.
 return <CloudSource key={molecule.cloud} molecule={molecule} {...props}/>;
}

function CloudSource({molecule,...props}:Props){
 const [failed,setFailed]=useState(false);
 return <img {...props} src={failed?(molecule.cloud_fallback||molecule.cloud):molecule.cloud}
  onError={()=>{if(!failed&&molecule.cloud_fallback)setFailed(true);}}/>;
}
