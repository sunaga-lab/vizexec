/**
 * @file  VizexecLogWriter.cpp
 * @brief Log Writer for VizEXEC
 *
 * @author Sunagae
 * @date 2011-02-11
 * 
 */
#include <string>
#include <boost/thread.hpp>
#include <boost/thread/condition.hpp>
#include <boost/lexical_cast.hpp>
#include <boost/algorithm/string.hpp>
#include <sstream>

#include <fstream>
#include <iostream>
#include <list>
#include <vector>

#include <stdio.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>

#include "VizexecLogWriter.hpp"

using namespace std;
using namespace boost;

/// Size of log buffer, when become full, program will be blocked at the markers.
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

	WriteComment("Start VizEXEC ");
	WriteComment("writer: cpp-vlw");
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
    buf->LogType = "CAL";
	buf->LogFlag = LF_FUNCNAME;
	buf->FuncName = func_name_;
	PutLogData(buf);
}

func_tracer::~func_tracer()
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "RET";
	buf->LogFlag = LF_FUNCNAME;
	buf->FuncName = func_name_;
	PutLogData(buf);
}

void WritePhase(const char *func)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "PHS";
	buf->LogFlag = LF_FUNCNAME;
	buf->FuncName = func;
	PutLogData(buf);
}


void WriteRecv(const void *p1, const void *p2)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "RCV";
	buf->LogFlag = LF_PTRDATA;
	buf->PtrData1 = p1;
	buf->PtrData2 = p2;
	PutLogData(buf);
}

void WriteSend(const void *p1, const void *p2)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "SND";
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

void WriteInfo(const string &info)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "INF";
	buf->LogFlag = LF_STRDATA | LF_NOTIME;
	buf->StrData1 = info;
	PutLogData(buf);
}

void WriteTerminate()
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "TRM";
	buf->LogFlag = 0;
	PutLogData(buf);
}

void SetCurrentThreadName(const string &name)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "TNM";
	buf->LogFlag = LF_STRDATA | LF_NOTIME;
	buf->StrData1 = name;
	PutLogData(buf);
}

void WriteEvent(const string &eventstr)
{
	ONLY_IF_LOGWRITER_ENABLED
	LogData *buf = NewLogBuffer();
    buf->LogType = "EVT";
	buf->LogFlag = LF_STRDATA;
	buf->StrData1 = eventstr;
	PutLogData(buf);
}



class LogWriter
{
protected:
    bool error_;
public:
    LogWriter(){error_ = false;}
    virtual ~LogWriter(){}
    bool IsError(){return error_;}
    virtual void Write(const string &line) = 0;
    virtual void Close() = 0;
};

class FileLogWriter: public LogWriter
{
    ofstream strm_;
public:
    FileLogWriter(const string &fn)
        :strm_(fn.c_str())
    {
        if(strm_.bad() || strm_.fail())
        {
            error_ = true;
            return;
        }
    }
    void Write(const string &line)
    {
        strm_.write(line.c_str(), line.length());
    }
    void Close()
    {
        strm_.close();
    }
};

class SocketLogWriter: public LogWriter
{
    int socket_;
public:
    SocketLogWriter(const string &host, int port)
    {
        string service = lexical_cast<string>(port);
        socket_ = -1;
        struct addrinfo hints, *res0;
        memset(&hints, 0, sizeof(hints));
        hints.ai_socktype = SOCK_STREAM;
        hints.ai_family = PF_UNSPEC;
        int err;
        if((err = getaddrinfo(host.c_str(), service.c_str(), &hints, &res0)) != 0)
        {
            error_ = true;
            return;
        }

        for(addrinfo *res = res0; res != NULL; res = res->ai_next)
        {
            int sock = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
            if(sock < 0)
            {
                continue;
            }
            if(connect(sock, res->ai_addr, res->ai_addrlen) != 0)
            {
                close(sock);
                continue;
            }
            socket_ = sock;
            break;
        }
        freeaddrinfo(res0);
        if(socket_ == -1)
        {
            error_ = true;
        }
        cout << "VZE: Connected to " << host << ":" << port << endl;
    }
    void Write(const string &line)
    {
        if(error_)
            return;
        string buf = line;
        while(true)
        {
            int len_sent = send(socket_, buf.c_str(), buf.length(), 0);
            if(len_sent <= 0)
            {
                cerr << "VZE: Disconnected." << endl;
                error_ = true;
                return;
            }
            if(len_sent >= line.length())
                break;
            buf = buf.substr(len_sent);
        }
    }
    void Close()
    {
        close(socket_);
    }
};

static LogWriter *g_writer_;
void LogWriteThreadMain()
{
	string fn_env;
    if(getenv("VIZEXEC_LOGFILE"))
        fn_env = getenv("VIZEXEC_LOGFILE");
	if(fn_env.length() == 0)
	{
		fn_env = "vizexec.log";
	}

    if(fn_env.substr(0, 4) == string("tcp:"))
    {
        vector<string> v;
        algorithm::split(v, fn_env, is_any_of(":"));
        g_writer_ = new SocketLogWriter(v[1], lexical_cast<int>(v[2]));
    }
    else
    {
        g_writer_ = new FileLogWriter(fn_env);
    }
	if(g_writer_->IsError())
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
            stringstream strm;            
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
            g_writer_->Write(strm.str());
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
    g_writer_->Close();
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
