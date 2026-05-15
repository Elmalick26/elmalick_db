"""
نظام النسخ الاحتياطي التلقائي
Auto Backup System
"""

import sqlite3
import shutil
import os
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
import gzip

import db_path as db_paths_module
# دمج نظام التسجيل الموحد الذي قمنا بإنشائه
from app_logger import AppLogger 


class AutoBackupSystem:
    """نظام النسخ الاحتياطي التلقائي"""
    
    def __init__(self, db_path=None, backup_dir=None):
        self.db_path = db_path if db_path else db_paths_module.get_db_path()
        self.backup_dir = Path(backup_dir) if backup_dir else Path(os.path.join(os.path.dirname(os.path.abspath(self.db_path)), "backups"))
        
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            AppLogger.error("AutoBackup", f"فشل في إنشاء مجلد النسخ الاحتياطي: {e}")

        self.is_running = False
        self.backup_thread = None
    
    def _log(self, level, message):
        """تسجيل الرسائل عبر نظام AppLogger الموحد بدلاً من ملف منفصل"""
        if level == "info":
            AppLogger.info("AutoBackup", message)
        elif level == "warning":
            AppLogger.warning("AutoBackup", message)
        elif level == "error":
            AppLogger.error("AutoBackup", message)
    
    def create_backup(self, compress=True):
        """إنشاء نسخة احتياطية"""
        try:
            if not os.path.exists(self.db_path):
                self._log("error", f"قاعدة البيانات غير موجودة: {self.db_path}")
                return None
            
            # اسم الملف مع التاريخ والوقت
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"backup_auto_{timestamp}.db"
            
            # نسخ قاعدة البيانات
            shutil.copy2(self.db_path, backup_file)
            
            # ضغط النسخة الاحتياطية
            if compress:
                compressed_file = self.backup_dir / f"backup_auto_{timestamp}.db.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # حذف النسخة غير المضغوطة
                os.remove(backup_file)
                backup_file = compressed_file
            
            self._log("info", f"تم إنشاء نسخة احتياطية بنجاح: {backup_file.name}")
            
            # حذف النسخ القديمة للحفاظ على مساحة القرص
            self.cleanup_old_backups(keep_days=30)
            
            return str(backup_file)
            
        except Exception as e:
            self._log("error", f"فشل إنشاء النسخة الاحتياطية: {str(e)}")
            return None
    
    def cleanup_old_backups(self, keep_days=30):
        """حذف النسخ الاحتياطية القديمة"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            for backup_file in self.backup_dir.glob("backup_*.db*"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    backup_file.unlink()
                    self._log("info", f"تم حذف نسخة قديمة: {backup_file.name}")
        
        except Exception as e:
            self._log("warning", f"خطأ في تنظيف النسخ القديمة: {str(e)}")
    
    def restore_backup(self, backup_file):
        """استعادة من نسخة احتياطية"""
        try:
            backup_path = Path(backup_file)
            
            if not backup_path.exists():
                self._log("error", f"النسخة الاحتياطية غير موجودة: {backup_file}")
                return False
            
            # إنشاء نسخة أمان من الحالي قبل الاستعادة
            if os.path.exists(self.db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safety_backup = self.backup_dir / f"safety_before_restore_{timestamp}.db"
                shutil.copy2(self.db_path, safety_backup)
                self._log("info", f"تم إنشاء نسخة أمان ما قبل الاستعادة: {safety_backup.name}")
            
            # استعادة النسخة
            if backup_path.suffix == '.gz':
                # فك الضغط أولاً
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, self.db_path)
            
            self._log("info", f"تم استعادة النسخة الاحتياطية بنجاح: {backup_path.name}")
            return True
            
        except Exception as e:
            self._log("error", f"فشلت الاستعادة: {str(e)}")
            return False
    
    def list_backups(self):
        """عرض قائمة النسخ الاحتياطية"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups

        for backup_file in sorted(self.backup_dir.glob("backup_*.db*"), reverse=True):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                file_size_mb = backup_file.stat().st_size / (1024 * 1024)  # MB
                
                backups.append({
                    'file': str(backup_file),
                    'filename': backup_file.name,
                    'name': backup_file.name,
                    'date': file_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': f"{file_size_mb:.2f} MB",
                    'size_mb': file_size_mb
                })
            except Exception:
                continue
        
        return backups
    
    def schedule_auto_backup(self, interval_hours=24):
        """جدولة النسخ الاحتياطي التلقائي"""
        schedule.every(interval_hours).hours.do(self.create_backup)
        self._log("info", f"تم جدولة النسخ الاحتياطي التلقائي كل {interval_hours} ساعة")
    
    def start_auto_backup(self, interval_hours=24):
        """بدء النسخ الاحتياطي التلقائي في خيط منفصل (Background Thread)"""
        if self.is_running:
            self._log("warning", "نظام النسخ الاحتياطي التلقائي يعمل بالفعل")
            return
        
        self.is_running = True
        self.schedule_auto_backup(interval_hours)
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # تحقق كل دقيقة لتخفيف الحمل على المعالج
        
        self.backup_thread = Thread(target=run_scheduler, daemon=True)
        self.backup_thread.start()
        
        self._log("info", "تم بدء خدمة النسخ الاحتياطي التلقائي في الخلفية")
    
    def stop_auto_backup(self):
        """إيقاف النسخ الاحتياطي التلقائي"""
        self.is_running = False
        schedule.clear()
        self._log("info", "تم إيقاف خدمة النسخ الاحتياطي التلقائي")
    
    def backup_on_startup(self):
        """إنشاء نسخة احتياطية فورية عند بدء البرنامج (يُنصح بربطها بتشغيل النظام)"""
        self._log("info", "بدء إنشاء نسخة احتياطية أولية عند تشغيل النظام...")
        return self.create_backup(compress=True)
    
    def get_backup_stats(self):
        """إحصائيات النسخ الاحتياطية"""
        backups = self.list_backups()
        try:
            total_size = sum(Path(b['file']).stat().st_size for b in backups)
            total_mb = total_size / (1024 * 1024)
        except Exception:
            total_mb = 0.0
            
        return {
            'total_backups': len(backups),
            'total_size_mb': total_mb,
            'oldest_backup': backups[-1]['date'] if backups else 'لا توجد',
            'newest_backup': backups[0]['date'] if backups else 'لا توجد'
        }

# مثال على الاستخدام
if __name__ == "__main__":
    # تشغيل وهمي لاختبار النظام
    backup_system = AutoBackupSystem()
    print("=== نظام النسخ الاحتياطي التلقائي ===\n")
    
    # إنشاء نسخة احتياطية
    backup_file = backup_system.create_backup(compress=True)
    
    # عرض قائمة النسخ
    print("\n=== قائمة النسخ الاحتياطية ===")
    backups = backup_system.list_backups()
    for i, backup in enumerate(backups[:5], 1):
        print(f"{i}. {backup['name']} - {backup['date']} - {backup['size']}")
    
    # عرض الإحصائيات
    print("\n=== الإحصائيات ===")
    stats = backup_system.get_backup_stats()
    print(f"عدد النسخ: {stats['total_backups']}")
    print(f"الحجم الكلي: {stats['total_size_mb']:.2f} MB")
    print(f"أحدث نسخة: {stats['newest_backup']}")
    print(f"أقدم نسخة: {stats['oldest_backup']}")
    
    print("\n✅ نظام النسخ الاحتياطي يعمل بشكل صحيح")