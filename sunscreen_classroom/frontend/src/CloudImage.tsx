import type {ImgHTMLAttributes} from 'react';
import type {Molecule} from './types';
import {OptimizedImage} from './OptimizedImage';

type Props = Omit<ImgHTMLAttributes<HTMLImageElement>,'src'> & {molecule:Molecule};

export function CloudImage({molecule,...props}:Props){
 return <OptimizedImage {...props} src={molecule.cloud} fallbackSrc={molecule.cloud_fallback}/>;
}
