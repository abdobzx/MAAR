#!/bin/bash

# Database Maintenance and Optimization Script
# This script performs automated database maintenance tasks

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/enterprise-rag/database-maintenance.log"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-enterprise_rag}"
DB_USER="${DB_USER:-rag_user}"
BACKUP_RETENTION_DAYS=7
VACUUM_THRESHOLD_DAYS=1
ANALYZE_THRESHOLD_DAYS=1

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check if database is accessible
check_database() {
    log "Checking database connectivity..."
    
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
        error_exit "Database is not accessible"
    fi
    
    log "Database connectivity verified"
}

# Get database statistics
get_db_stats() {
    log "Gathering database statistics..."
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT 
        schemaname,
        tablename,
        n_tup_ins as inserts,
        n_tup_upd as updates,
        n_tup_del as deletes,
        n_live_tup as live_tuples,
        n_dead_tup as dead_tuples,
        last_vacuum,
        last_autovacuum,
        last_analyze,
        last_autoanalyze
    FROM pg_stat_user_tables
    ORDER BY n_dead_tup DESC;
    " >> "$LOG_FILE"
}

# Perform VACUUM on tables with high dead tuple ratio
vacuum_tables() {
    log "Starting VACUUM operation..."
    
    # Get tables that need vacuuming (dead tuples > 10% of total)
    tables_to_vacuum=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT tablename 
    FROM pg_stat_user_tables 
    WHERE n_dead_tup > (n_live_tup + n_dead_tup) * 0.1 
    AND n_dead_tup > 1000
    OR last_vacuum < NOW() - INTERVAL '$VACUUM_THRESHOLD_DAYS days'
    OR last_vacuum IS NULL;
    ")
    
    if [ -n "$tables_to_vacuum" ]; then
        for table in $tables_to_vacuum; do
            table=$(echo "$table" | xargs)  # trim whitespace
            if [ -n "$table" ]; then
                log "Vacuuming table: $table"
                psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "VACUUM VERBOSE $table;" >> "$LOG_FILE" 2>&1
            fi
        done
    else
        log "No tables require vacuuming"
    fi
}

# Perform ANALYZE on tables
analyze_tables() {
    log "Starting ANALYZE operation..."
    
    # Get tables that need analyzing
    tables_to_analyze=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT tablename 
    FROM pg_stat_user_tables 
    WHERE last_analyze < NOW() - INTERVAL '$ANALYZE_THRESHOLD_DAYS days'
    OR last_analyze IS NULL;
    ")
    
    if [ -n "$tables_to_analyze" ]; then
        for table in $tables_to_analyze; do
            table=$(echo "$table" | xargs)  # trim whitespace
            if [ -n "$table" ]; then
                log "Analyzing table: $table"
                psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "ANALYZE VERBOSE $table;" >> "$LOG_FILE" 2>&1
            fi
        done
    else
        log "No tables require analyzing"
    fi
}

# Reindex tables if needed
reindex_tables() {
    log "Checking for tables requiring reindexing..."
    
    # Check for bloated indexes (simplified check)
    bloated_indexes=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT indexrelname 
    FROM pg_stat_user_indexes 
    WHERE idx_scan = 0 
    AND pg_relation_size(indexrelid) > 10485760;  -- 10MB
    ")
    
    if [ -n "$bloated_indexes" ]; then
        for index in $bloated_indexes; do
            index=$(echo "$index" | xargs)  # trim whitespace
            if [ -n "$index" ]; then
                log "Reindexing: $index"
                psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "REINDEX INDEX CONCURRENTLY $index;" >> "$LOG_FILE" 2>&1 || true
            fi
        done
    else
        log "No indexes require reindexing"
    fi
}

# Clean up old data
cleanup_old_data() {
    log "Cleaning up old data..."
    
    # Clean old logs (keep last 30 days)
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    DELETE FROM system_logs 
    WHERE created_at < NOW() - INTERVAL '30 days';
    " >> "$LOG_FILE" 2>&1 || log "No system_logs table found or cleanup failed"
    
    # Clean old analytics data (keep last 90 days)
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    DELETE FROM analytics_events 
    WHERE created_at < NOW() - INTERVAL '90 days';
    " >> "$LOG_FILE" 2>&1 || log "No analytics_events table found or cleanup failed"
    
    # Clean old temporary files records
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    DELETE FROM temp_files 
    WHERE created_at < NOW() - INTERVAL '7 days';
    " >> "$LOG_FILE" 2>&1 || log "No temp_files table found or cleanup failed"
    
    log "Data cleanup completed"
}

# Update database statistics
update_statistics() {
    log "Updating database statistics..."
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT pg_stat_reset();
    " >> "$LOG_FILE" 2>&1
    
    log "Statistics updated"
}

# Check database size and growth
check_database_size() {
    log "Checking database size and growth..."
    
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT 
        pg_database.datname,
        pg_size_pretty(pg_database_size(pg_database.datname)) AS size
    FROM pg_database
    WHERE pg_database.datname = '$DB_NAME';
    
    SELECT 
        schemaname,
        tablename,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
        pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS index_size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
    LIMIT 10;
    " >> "$LOG_FILE"
}

# Optimize PostgreSQL configuration
optimize_config() {
    log "Checking PostgreSQL configuration optimization opportunities..."
    
    # Check current settings
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT name, setting, unit, context, short_desc
    FROM pg_settings
    WHERE name IN (
        'shared_buffers',
        'effective_cache_size',
        'maintenance_work_mem',
        'checkpoint_completion_target',
        'wal_buffers',
        'default_statistics_target',
        'random_page_cost',
        'effective_io_concurrency'
    );
    " >> "$LOG_FILE"
}

# Generate maintenance report
generate_report() {
    log "Generating maintenance report..."
    
    local report_file="/tmp/db-maintenance-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "Database Maintenance Report - $(date)"
        echo "=========================================="
        echo ""
        echo "Database Size:"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT pg_size_pretty(pg_database_size('$DB_NAME')) AS database_size;
        "
        echo ""
        echo "Top 10 Largest Tables:"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT 
            tablename,
            pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size('public.'||tablename) DESC
        LIMIT 10;
        "
        echo ""
        echo "Tables Requiring Attention:"
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT 
            tablename,
            n_dead_tup,
            n_live_tup,
            ROUND(n_dead_tup::float / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_tuple_percent,
            last_vacuum,
            last_analyze
        FROM pg_stat_user_tables
        WHERE n_dead_tup > 1000
        ORDER BY dead_tuple_percent DESC;
        "
    } > "$report_file"
    
    log "Maintenance report generated: $report_file"
}

# Main execution
main() {
    log "Starting database maintenance script"
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Perform maintenance tasks
    check_database
    get_db_stats
    vacuum_tables
    analyze_tables
    reindex_tables
    cleanup_old_data
    check_database_size
    optimize_config
    generate_report
    
    log "Database maintenance completed successfully"
}

# Run main function
main "$@"
