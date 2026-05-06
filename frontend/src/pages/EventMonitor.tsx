import React, { useState, useEffect } from 'react';
import { api, NewsItem } from '@/src/api/client';
import { Button } from '@/src/components/ui/button';
import { Input } from '@/src/components/ui/input';
import { Badge } from '@/src/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/src/components/ui/dialog';
import { Label } from '@/src/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/src/components/ui/table';
import { Newspaper, Plus, Loader2, ExternalLink, Calendar, User, Building2 } from 'lucide-react';
import { toast } from 'sonner';

export function EventMonitor() {
  const [records, setRecords] = useState<NewsItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formEntrytime, setFormEntrytime] = useState('');
  const [formMedianame, setFormMedianame] = useState('');
  const [formAuthors, setFormAuthors] = useState('');
  const [formAbs, setFormAbs] = useState('');
  const [formOriginalurl, setFormOriginalurl] = useState('');

  const pageSize = 10;

  const loadNews = async (page: number) => {
    setLoading(true);
    try {
      const result = await api.getNewsList(page, pageSize);
      if (result.success && result.data) {
        setRecords(result.data.records || []);
        setTotal(result.data.total);
        setTotalPages(result.data.totalPages);
        setCurrentPage(result.data.page);
      }
    } catch (err: any) {
      toast.error('加载新闻列表失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadNews(1); }, []);

  const handleCreate = async () => {
    if (!formTitle) { toast.error('标题不能为空'); return; }
    setSaving(true);
    try {
      await api.createNews({
        texttitle: formTitle,
        entrytime: formEntrytime || null,
        medianame: formMedianame,
        authors: formAuthors,
        abs: formAbs,
        originalurl: formOriginalurl,
      });
      toast.success('新闻添加成功');
      setCreateDialogOpen(false);
      resetForm();
      loadNews(1);
    } catch (err: any) {
      toast.error('添加失败: ' + err.message);
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setFormTitle(''); setFormEntrytime(''); setFormMedianame('');
    setFormAuthors(''); setFormAbs(''); setFormOriginalurl('');
  };

  const formatDateTime = (dt: string) => {
    if (!dt) return '-';
    return dt.replace('T', ' ').substring(0, 19);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">事件监测</h1>
          <p className="text-slate-500 text-sm mt-1">新闻资讯采集与监测，支持手工录入。</p>
        </div>
        <Button className="gap-2" onClick={() => setCreateDialogOpen(true)}>
          <Plus className="w-4 h-4" /> 新增新闻
        </Button>
      </div>

      <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-1.5 text-sm text-slate-500">
          <Newspaper className="w-4 h-4 text-blue-500" />
          <span>共 <strong className="text-slate-700">{total}</strong> 条新闻</span>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-slate-400">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> 加载中...
          </div>
        ) : records.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-slate-400">暂无新闻数据</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="bg-slate-50/50">
                <TableHead className="w-[300px]">标题</TableHead>
                <TableHead className="w-[160px]">事件时间</TableHead>
                <TableHead className="w-[120px]">媒体名称</TableHead>
                <TableHead className="w-[100px]">作者</TableHead>
                <TableHead>摘要</TableHead>
                <TableHead className="w-[80px]">原文</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map(item => (
                <TableRow key={item.id} className="hover:bg-slate-50">
                  <TableCell className="font-medium text-slate-900 max-w-[300px]">
                    <div className="truncate" title={item.texttitle}>{item.texttitle}</div>
                  </TableCell>
                  <TableCell className="text-xs text-slate-500 whitespace-nowrap">
                    <div className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDateTime(item.entrytime)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="text-xs bg-blue-50 border-blue-200 text-blue-700">
                      <Building2 className="w-3 h-3 mr-1" />
                      {item.medianame || '-'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-xs text-slate-600">
                    <div className="flex items-center gap-1">
                      <User className="w-3 h-3 text-slate-400" />
                      {item.authors || '-'}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-slate-600 max-w-[300px]">
                    <div className="line-clamp-2" title={item.abs}>{item.abs || '-'}</div>
                  </TableCell>
                  <TableCell>
                    {item.originalurl ? (
                      <a href={item.originalurl} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-blue-500 hover:text-blue-700 text-xs">
                        <ExternalLink className="w-3 h-3" /> 查看
                      </a>
                    ) : (
                      <span className="text-xs text-slate-400">-</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button variant="outline" size="sm" onClick={() => loadNews(currentPage - 1)} disabled={currentPage <= 1}>
            上一页
          </Button>
          <span className="text-sm text-slate-600">第 {currentPage} / {totalPages} 页</span>
          <Button variant="outline" size="sm" onClick={() => loadNews(currentPage + 1)} disabled={currentPage >= totalPages}>
            下一页
          </Button>
        </div>
      )}

      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新增新闻资讯</DialogTitle>
            <DialogDescription>手工录入新闻资讯，数据将持久化到数据库。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>标题 *</Label>
              <Input value={formTitle} onChange={e => setFormTitle(e.target.value)} placeholder="新闻标题" />
            </div>
            <div className="space-y-2">
              <Label>事件发生时间</Label>
              <Input type="datetime-local" value={formEntrytime} onChange={e => setFormEntrytime(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>媒体名称</Label>
              <Input value={formMedianame} onChange={e => setFormMedianame(e.target.value)} placeholder="例如：新华社" />
            </div>
            <div className="space-y-2">
              <Label>作者</Label>
              <Input value={formAuthors} onChange={e => setFormAuthors(e.target.value)} placeholder="作者姓名" />
            </div>
            <div className="space-y-2">
              <Label>摘要</Label>
              <textarea className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                value={formAbs} onChange={e => setFormAbs(e.target.value)} placeholder="新闻摘要内容" />
            </div>
            <div className="space-y-2">
              <Label>原文 URL</Label>
              <Input value={formOriginalurl} onChange={e => setFormOriginalurl(e.target.value)} placeholder="https://..." />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>取消</Button>
            <Button onClick={handleCreate} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
