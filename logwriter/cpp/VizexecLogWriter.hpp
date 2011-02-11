/**
 * @file  VizexecLogWriter.hpp
 * @brief Log Writer for VizEXEC
 *
 * @author Sunagae
 * @date 2011-02-11
 * 
 * Log Writer for VizEXEC visualization.
 * You can visualize your program with writing the Marker Macro where you want to be.
 * Details are in the macro's comment or the web site.
 * 
 * Log writing processing are threadized, so I belive there is only few overhead...
 * 
 */

#ifndef VIZEXEC_LOGWRITER_HPP_
#define VIZEXEC_LOGWRITER_HPP_

#include <string>
#include <boost/thread.hpp>


#ifdef ENABLE_VIZEXEC
/// Marker for beginning log writer, must called before all other marker macros
#	define VZE_START \
		vizexec::EnableLogWriter();
/// Marker for functions
#	define VZE_FUNC 	\
		vizexec::func_tracer __vzp_tracer(__func__);
/// Marker for functions with appearing other name
#	define VZE_FUNCCUSTOM(name) \
		vizexec::func_tracer __vzp_tracer(name);
/// Marker of phase change
#	define VZE_PHASE(name) \
		vizexec::WritePhase(name);
/// Marker of message sending
#	define VZE_SEND1(ptr)		\
		vizexec::WriteSend(vizexec::get_ptr(ptr));
/// Marker of message receiving
#	define VZE_RECV1(ptr)		\
		vizexec::WriteRecv(vizexec::get_ptr(ptr));
/// Marker of message sending (2 params)
#	define VZE_SEND2(p1, p2)		\
		vizexec::WriteSend(vizexec::get_ptr(p1), vizexec::get_ptr(p2));
/// Marker of message receiving (2 params)
#	define VZE_RECV2(p1, p2)		\
		vizexec::WriteRecv(vizexec::get_ptr(p1), vizexec::get_ptr(p2));
/// Marker of events
#	define VZE_EVENT(str)		\
		vizexec::WriteEvent(str);

/// Marker of thread name
#	define VZE_THREADNAME(name)		\
		vizexec::SetCurrentThreadName(name);

#else
#   define VZE_START
#	define VZE_FUNC
#	define VZE_FUNCCUSTOM(name)
#	define VZE_PHASE(name)
#	define VZE_SEND1(ptr)
#	define VZE_RECV1(ptr)
#	define VZE_RECV2(p1,p2)
#	define VZE_SEND2(p1,p2)
#   define VZE_EVENT(str)
#   define VZE_THREADNAME(name)
#endif


namespace vizexec
{
using std::string;
typedef unsigned long long trace_time_t;

class func_tracer
{
	const char *func_name_;
public:
	func_tracer(const char *func);
	~func_tracer();
};


template<typename T>
inline const void* get_ptr(T* value)
{
	return value;
}

inline const void* get_ptr(int value)
{
    return *((void **)&value);
}


// for Smart pointers
/*
template<typename T>
inline void* get_ptr(shared_ptr<T> value)
{
	return value.get();
}
*/

int GetCurrentThreadID();
void SetCurrentThreadName(const string &name);

void EnableLogWriter();
bool IsLogWriterEnabled();

void WriteRecv(const void *p1, const void *p2 = NULL);
void WriteSend(const void *p1, const void *p2 = NULL);
void WriteComment(const string &comment);
void WriteEvent(const string &comment);
void WritePhase(const char *phase_name);

}



#endif /* VIZEXEC_LOGWRITER_HPP_ */
