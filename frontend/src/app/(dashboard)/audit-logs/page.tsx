'use client';

import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AuditLogFiltersComponent } from '@/components/audit/audit-log-filters';
import { AuditLogTable } from '@/components/audit/audit-log-table';
import { LoginLogTable } from '@/components/audit/login-log-table';
import { useAuditLogs, useLoginLogs } from '@/lib/hooks/use-audit';
import { usePermissions } from '@/lib/hooks/use-permissions';
import { redirect } from 'next/navigation';

export default function AuditLogsPage() {
  const { canViewAuditLogs } = usePermissions();
  const [activeTab, setActiveTab] = useState('operations');
  
  const {
    data: auditData,
    isLoading: auditLoading,
    filters: auditFilters,
    updateFilters: updateAuditFilters,
    setPage: setAuditPage,
    resetFilters: resetAuditFilters,
  } = useAuditLogs();
  
  const {
    data: loginData,
    isLoading: loginLoading,
    filters: loginFilters,
    setPage: setLoginPage,
  } = useLoginLogs();
  
  // Check permission
  if (!canViewAuditLogs()) {
    redirect('/items');
  }
  
  const auditLogs = auditData?.results || [];
  const auditTotalCount = auditData?.count || 0;
  const auditTotalPages = Math.ceil(auditTotalCount / (auditFilters.page_size || 20));
  
  const loginLogs = loginData?.results || [];
  const loginTotalCount = loginData?.count || 0;
  const loginTotalPages = Math.ceil(loginTotalCount / (loginFilters.page_size || 20));
  
  return (
    <div className="container mx-auto py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">审计日志</h1>
        <p className="text-muted-foreground">查看系统操作记录和用户登录日志</p>
      </div>
      
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="operations">操作日志</TabsTrigger>
          <TabsTrigger value="logins">登录日志</TabsTrigger>
        </TabsList>
        
        <TabsContent value="operations" className="space-y-4">
          <AuditLogFiltersComponent
            filters={auditFilters}
            onFiltersChange={updateAuditFilters}
            onReset={resetAuditFilters}
          />
          <AuditLogTable
            logs={auditLogs}
            isLoading={auditLoading}
            page={auditFilters.page || 1}
            totalPages={auditTotalPages}
            totalCount={auditTotalCount}
            onPageChange={setAuditPage}
          />
        </TabsContent>
        
        <TabsContent value="logins" className="space-y-4">
          <LoginLogTable
            logs={loginLogs}
            isLoading={loginLoading}
            page={loginFilters.page || 1}
            totalPages={loginTotalPages}
            totalCount={loginTotalCount}
            onPageChange={setLoginPage}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
