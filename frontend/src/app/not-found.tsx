import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { FileQuestion } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="text-center space-y-4">
        <FileQuestion className="h-16 w-16 mx-auto text-muted-foreground" />
        <h1 className="text-2xl font-semibold">页面不存在</h1>
        <p className="text-muted-foreground">
          您访问的页面不存在或已被移除
        </p>
        <Button asChild>
          <Link href="/items">返回首页</Link>
        </Button>
      </div>
    </div>
  );
}
