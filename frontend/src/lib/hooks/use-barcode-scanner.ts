'use client';
import { useCallback,useEffect,useRef,useState } from 'react';
import { BrowserMultiFormatReader,type IScannerControls } from '@zxing/browser';
import { NotFoundException } from '@zxing/library';
interface Options { onScan:(barcode:string,format:string)=>void; onError?:(error:Error)=>void; }
export function useBarcodeScanner({onScan,onError}:Options){
 const videoRef=useRef<HTMLVideoElement>(null);const controlsRef=useRef<IScannerControls|null>(null);const readerRef=useRef<BrowserMultiFormatReader|null>(null);const [isScanning,setScanning]=useState(false);const [hasPermission,setPermission]=useState<boolean|null>(null);const [error,setError]=useState<string|null>(null);
 const stopScanning=useCallback(()=>{controlsRef.current?.stop();controlsRef.current=null;setScanning(false);const stream=videoRef.current?.srcObject as MediaStream|null;stream?.getTracks().forEach(t=>t.stop());if(videoRef.current)videoRef.current.srcObject=null;},[]);
 const startScanning=useCallback(async()=>{if(!videoRef.current||isScanning)return;setError(null);try{const reader=readerRef.current??new BrowserMultiFormatReader();readerRef.current=reader;const controls=await reader.decodeFromConstraints({audio:false,video:{facingMode:{ideal:'environment'}}},videoRef.current,(result,err)=>{if(result){onScan(result.getText(),String(result.getBarcodeFormat()));try{navigator.vibrate?.(80);}catch{}}else if(err && !(err instanceof NotFoundException)){const e=err instanceof Error?err:new Error(String(err));setError(e.message);onError?.(e);}});controlsRef.current=controls;setPermission(true);setScanning(true);}catch(e){const err=e instanceof Error?e:new Error(String(e));const denied=err.name==='NotAllowedError'||err.name==='PermissionDeniedError';if(denied)setPermission(false);setError(err.message||'无法启动摄像头');setScanning(false);onError?.(err);}},[isScanning,onError,onScan]);
 useEffect(()=>()=>stopScanning(),[stopScanning]);
 return{startScanning,stopScanning,isScanning,hasPermission,error,videoRef};
}
