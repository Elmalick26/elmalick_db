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


class AutoBackupSystem:
    """نظام النسخ الاحتياطي التلقائي"""
    
    def __init__(self, db_path=None, backup_dir=None):
        self.db_path = db_path if db_path else db_paths_module.get_db_path()
        self.backup_dir = Path(backup_dir) if backup_dir else Path(db_paths_module.get_backup_dir())
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.is_running = False
        self.backup_thread = None
    
    def _log_to_file(self, message):
        """تسجيل الرسالة في ملف بدلاً من console"""
        try:
            log_dir = Path(db_paths_module.get_logs_dir())
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "backup.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"{timestamp} - {message}\n")
        except:
            pass  # تجاهل أخطاء الكتابة
    
    def create_backup(self, compress=True):
        """إنشاء نسخة احتياطية"""
        try:
            if not os.path.exists(self.db_path):
                msg = f"❌ قاعدة البيانات غير موجودة: {self.db_path}"
                self._log_to_file(msg)
                return None
            
            # اسم الملف مع التاريخ والوقت
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = self.backup_dir / f"backup_{timestamp}.db"
            
            # نسخ قاعدة البيانات
            shutil.copy2(self.db_path, backup_file)
            
            # ضغط النسخة الاحتياطية
            if compress:
                compressed_file = self.backup_dir / f"backup_{timestamp}.db.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # حذف النسخة غير المضغوطة
                os.remove(backup_file)
                backup_file = compressed_file
            
            msg = f"✅ تم إنشاء نسخة احتياطية: {backup_file.name}"
            self._log_to_file(msg)
            
            # حذف النسخ القديمة
            self.cleanup_old_backups(keep_days=30)
            
            return str(backup_file)
            
        except Exception as e:
            msg = f"❌ فشل إنشاء النسخة الاحتياطية: {e}"
            self._log_to_file(msg)
            return None
    
    def cleanup_old_backups(self, keep_days=30):
        """حذف النسخ الاحتياطية القديمة"""
        try:
            cutoff_date = datetime.now() - timedelta(days=keep_days)
            
            for backup_file in self.backup_dir.glob("backup_*.db*"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    backup_file.unlink()
                    msg = f"🗑️ تم حذف نسخة قديمة: {backup_file.name}"
                    self._log_to_file(msg)
        
        except Exception as e:
            msg = f"⚠️ خطأ في تنظيف النسخ القديمة: {e}"
            self._log_to_file(msg)
    
    def restore_backup(self, backup_file):
        """استعادة من نسخة احتياطية"""
        try:
            backup_path = Path(backup_file)
            
            if not backup_path.exists():
                msg = f"❌ النسخة الاحتياطية غير موجودة: {backup_file}"
                self._log_to_file(msg)
                return False
            
            # إنشاء نسخة احتياطية من الحالي قبل الاستعادة
            if os.path.exists(self.db_path):
                safety_backup = f"{self.db_path}.before_restore"
                shutil.copy2(self.db_path, safety_backup)
                msg = f"💾 تم إنشاء نسخة أمان: {safety_backup}"
                self._log_to_file(msg)
            
            # استعادة النسخة
            if backup_path.suffix == '.gz':
                # فك الضغط أولاً
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(self.db_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, self.db_path)
            
            msg = f"✅ تم استعادة النسخة الاحتياطية: {backup_file}"
            self._log_to_file(msg)
            return True
            
        except Exception as e:
            msg = f"❌ فشلت الاستعادة: {e}"
            self._log_to_file(msg)
            return False
    
    def list_backups(self):
        """عرض قائمة النسخ الاحتياطية"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("backup_*.db*"), reverse=True):
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
        
        return backups
    
    def schedule_auto_backup(self, interval_hours=24):
        """جدولة النسخ الاحتياطي التلقائي"""
        schedule.every(interval_hours).hours.do(self.create_backup)
        msg = f"⏰ تم جدولة النسخ الاحتياطي كل {interval_hours} ساعة"
        self._log_to_file(msg)
    
    def start_auto_backup(self, interval_hours=24):
        """بدء النسخ الاحتياطي التلقائي في خيط منفصل"""
        if self.is_running:
            self._log_to_file("⚠️ النسخ الاحتياطي التلقائي يعمل بالفعل")
            return
        
        self.is_running = True
        self.schedule_auto_backup(interval_hours)
        
        def run_scheduler():
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # تحقق كل دقيقة
        
        self.backup_thread = Thread(target=run_scheduler, daemon=True)
        self.backup_thread.start()
        
        self._log_to_file("✅ تم بدء النسخ الاحتياطي التلقائي")
    
    def stop_auto_backup(self):
        """إيقاف النسخ الاحتياطي التلقائي"""
        self.is_running = False
        schedule.clear()
        self._log_to_file("⏹️ تم إيقاف النسخ الاحتياطي التلقائي")
    
    def backup_on_startup(self):
        """إنشاء نسخة احتياطية عند بدء البرنامج"""
        self._log_to_file("🚀 إنشاء نسخة احتياطية عند البدء...")
        return self.create_backup()
    
    def get_backup_stats(self):
        """إحصائيات النسخ الاحتياطية"""
        backups = self.list_backups()
        total_size = sum(Path(b['file']).stat().st_size for b in backups)
        
        return {
            'total_backups': len(backups),
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_backup': backups[-1]['date'] if backups else 'لا توجد',
            'newest_backup': backups[0]['date'] if backups else 'لا توجد'
        }


# مثال على الاستخدام
if __name__ == "__main__":
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
    
    print("\n✅ نظام النسخ الاحتياطي يعمل بشكل صحيح")
