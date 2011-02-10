
#include <string>
#include <boost/thread.hpp>
#include <boost/lexical_cast.hpp>
#include <fstream>
#include <iostream>
#include <list>

#include "VizexecLogWriter.hpp"

using namespace std;
using namespace boost;


#define LOG_BUFFER_MAX 1000


namespace vizexec
{

template<typename T>
class ListMT
{
	list<T> list_;
	mutex mtx_;
	condition append_condition_;
    typedef boost::mutex::scoped_lock lock_t;

public:
	void PushBack(const T &value)
	{
		lock_t lk(mtx_);
		list_.push_back(value);
		append_condition_.notify_one();
	}

	void PushFront(const T &value)
	{
		lock_t lk(mtx_);
		list_.push_front(value);
		append_condition_.notify_one();
	}

	void PopBack()
	{
		lock_t lk(mtx_);
		list_.pop_back();
	}

	void PopFront()
	{
		lock_t lk(mtx_);
		list_.pop_front();
	}

	T PopFrontValue()
	{
		lock_t lk(mtx_);
		if(list_.empty())
			return T();
		T value = list_.front();
		list_.pop_front();
		return value;
	}
	T PopFrontValueBlock()
	{
		lock_t lk(mtx_);
		while(true)
		{

			if(!list_.empty())
			{
				T value = list_.front();
				list_.pop_front();
				return value;
			}
			append_condition_.wait(lk);
		}
	}

	int Size()
	{
		lock_t lk(mtx_);
		return list_.size();
	}

	bool empty()
	{
		lock_t lk(mtx_);
		return list_.empty();
	}

	void clear()
	{
		lock_t lk(mtx_);
		return list_.clear();
	}

	T& Front()
	{
		lock_t lk(mtx_);
		return list_.front();
	}

	T& Back()
	{
		lock_t lk(mtx_);
		return list_.back();
	}


};





bool gEnabled = false;
    
mutex gThreadNameCounterMutex;
int gThreadNameCounter = 0;
thread_specific_ptr<string> gThreadName;
thread_specific_ptr<int> gThreadID;



const int LF_FUNCNAME   = 0x01;
const int LF_PTRDATA    = 0x02;
const int LF_STRDATA    = 0x04;
const int LF_NOTIME     = 0x08;

const int LF_SHUTDOWN   = 0x101;

mutex gTraceTimeMutex;
trace_time_t gTraceTime = 0;

mutex gLogWriteThreadMutex;
thread *gLogWriteThread;
bool gAtExitRegisterd = false;


int GetCurrentThreadID()
{
	if(!gThreadID.get())
	{
		int name_num;
		{
			mutex::scoped_lock lk(gThreadNameCounterMutex);
			name_num = gThreadNameCounter++;
		}
		gThreadID.reset(new int(name_num));
	}
	return *gThreadID.get();
}



trace_time_t GetCurrentTraceTime()
{
	mutex::scoped_lock lk(gTraceTimeMutex);
	return gTraceTime++;
}


// Log buffer
struct LogData
{
	int LogFlag;
    const char *LogType;
	int ThreadID;
	trace_time_t Time;
	const char *FuncName;
	string StrData1;
	const void *PtrData1;
	const void *PtrData2;
};

ListMT<LogData*> gLog;
ListMT<LogData*> gLogBuffer;
LogData* NewLogBuffer()
{
	LogData* buf;
	if(gLog.Size() > LOG_BUFFER_MAX)
	{
		cerr << "VizEXEC: Log buffer full. Suspend thread." << endl;
		while(gLog.Size() > LOG_BUFFER_MAX)
		{
			usleep(1000 * 100);
		}
		cerr << "VizEXEC: Resume thread" << endl;
	}
	if(!gLogBuffer.empty())
		buf = gLogBuffer.PopFrontValue();
	else
		buf = new LogData();

	buf->ThreadID = GetCurrentThreadID();
	buf->Time = GetCurrentTraceTime();

	return buf;
}



void LogWriteThreadMain();
void LogWriteThreadKill();

#define ONLY_IF_LOGWRITER_ENABLED		{if(!gEnabled) return;}
void EnableLogWriter()
{
	gEnabled = true;
    gLogWriteThread = new thread(&LogWriteThreadMain);
    if(!gAtExitRegisterd)
    {
        gAtExitRegisterd = true;
        atexit(LogWriteThreadKill);
    }

	WriteComment("Start VizEXEC cpp");
	cout << "VizEXEC: Waiting log write" << endl;
	while(!gLog.empty())
	{
		usleep(1000*50);
	}
	cout << "VizEXEC: Start" << endl;
}

bool IsLogWriterEnabled()
{
    return gEnabled;
}

void PutLogData(LogData *buf)
{
	gLog.PushBack(buf);
}

func_tracer::func_tracer(const char *func)
	:func_name_(func)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "C";
	buf->LogFlag = LF_FUNCNAME;
	buf->FuncName = func_name_;
	PutLogData(buf);
}

func_tracer::~func_tracer()
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "R";
	buf->LogFlag = LF_FUNCNAME;
	buf->FuncName = func_name_;
	PutLogData(buf);
}

void WritePhase(const char *func)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "P";
	buf->LogFlag = LF_FUNCNAME;
	buf->FuncName = func;
	PutLogData(buf);
}


void WriteRecv(const void *p1, const void *p2)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "V";
	buf->LogFlag = LF_PTRDATA;
	buf->PtrData1 = p1;
	buf->PtrData2 = p2;
	PutLogData(buf);
}

void WriteSend(const void *p1, const void *p2)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "S";
	buf->LogFlag = LF_PTRDATA;
	buf->PtrData1 = p1;
	buf->PtrData2 = p2;
	PutLogData(buf);
}


void WriteComment(const string &comment)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "#";
	buf->LogFlag = LF_STRDATA;
	buf->StrData1 = comment;
	PutLogData(buf);
}

void SetCurrentThreadName(const string &name)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "THREADNAME";
	buf->LogFlag = LF_STRDATA | LF_NOTIME;
	buf->StrData1 = name;
	PutLogData(buf);
}

void WriteEvent(const string &eventstr)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "E";
	buf->LogFlag = LF_STRDATA;
	buf->StrData1 = eventstr;
	PutLogData(buf);
}


void LogWriteThreadMain()
{
	const char *fn_env = getenv("VIZEXEC_LOGFILE");
	if(!fn_env || strlen(fn_env) == 0)
	{
		fn_env = "vizexec.log";
	}

	ofstream strm(fn_env);
	if(strm.bad() || strm.fail())
	{
		perror("VizEXEC: Log file open error");
		abort();
	}
	bool exit_flag = false;
	while(!exit_flag)
	{
		LogData *buf = gLog.PopFrontValueBlock();
        
        if(buf->LogFlag <= 0xFF)
        {
            strm << buf->LogType << " " << buf->ThreadID;
            if((buf->LogFlag & LF_NOTIME) == 0)
                strm << " " << buf->Time;
            if(buf->LogFlag & LF_FUNCNAME)
                strm << " " << buf->FuncName;
            if(buf->LogFlag & LF_PTRDATA)
                strm << " " << buf->PtrData1 << "_" << buf->PtrData2;
            if(buf->LogFlag & LF_STRDATA)
                strm << " \"" << buf->StrData1 << "\"";
            strm << endl;
            continue;
        }
        
		switch(buf->LogFlag)
		{
		case LF_SHUTDOWN:
			exit_flag = true;
			break;
		default: break;
		}
	}
	cout << "VizEXEC: Logger Shutdown" << endl;
	mutex::scoped_lock lk(gLogWriteThreadMutex);
	delete gLogWriteThread;
	gLogWriteThread = NULL;
}

void LogWriteThreadKill()
{
	cout << "VizEXEC: Joining writing thread" << endl;

	LogData *buf = NewLogBuffer();
	buf->ThreadID = GetCurrentThreadID();
	buf->Time = GetCurrentTraceTime();
	buf->LogFlag = LF_SHUTDOWN;
	gLog.PushBack(buf);

	while(true)
	{
		usleep(200 * 1000);
		mutex::scoped_lock lk(gLogWriteThreadMutex);
		if(!gLogWriteThread)
			break;
	}
}

}
