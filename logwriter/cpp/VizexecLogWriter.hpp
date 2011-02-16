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
#include <sstream>
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
		vizexec::WriteSend(vizexec::get_hash(ptr));
/// Marker of message receiving
#	define VZE_RECV1(ptr)		\
		vizexec::WriteRecv(vizexec::get_hash(ptr));
/// Marker of message sending (2 params)
#	define VZE_SEND2(p1, p2)		\
		vizexec::WriteSend(vizexec::hash_value_merge(vizexec::get_hash(p1), vizexec::get_hash(p2)));
/// Marker of message receiving (2 params)
#	define VZE_RECV2(p1, p2)		\
		vizexec::WriteRecv(vizexec::hash_value_merge(vizexec::get_hash(p1), vizexec::get_hash(p2)));
/// Marker of events
#	define VZE_EVENT(str)		\
		vizexec::WriteEvent(str);

/// Marker of information
#	define VZE_INFO(str)		\
		vizexec::WriteInfo(str);

/// Marker of information
#	define VZE_INFO_S(str_op)		\
		{std::stringstream strm; strm << str_op; vizexec::WriteInfo(strm.str());}


#	define VZE_INFO_VAL(name, value)		\
        VZE_INFO_S(name << " = " << value)
        
/// Marker of thread termination
#	define VZE_TERMINATE		\
		vizexec::WriteTerminate();

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
#   define VZE_INFO(str)
#   define VZE_INFO_STRM(str)
#   define VZE_TERMINATE(str)
#   define VZE_THREADNAME(name)
#endif


namespace vizexec
{
using std::string;

typedef unsigned long long int hashed_value_t;
typedef unsigned long long int trace_time_t;

class func_tracer
{
	const char *func_name_;
public:
	func_tracer(const char *func);
	~func_tracer();
};


template<typename T>
inline hashed_value_t get_hash(T* value)
{
	return (hashed_value_t)value;
}

inline hashed_value_t get_hash(int value)
{
    return (hashed_value_t)value;
}

inline hashed_value_t get_hash(const string &value)
{
    hashed_value_t val = 0;
    int m = value.length() / sizeof(hashed_value_t);
    for(int i = 0; i < m; i++)
    {
        val ^= ((hashed_value_t *)value.c_str())[i];
    }
    if(m*sizeof(hashed_value_t) == value.length())
        return val;

    hashed_value_t rem = 0;
    memcpy(
        &rem,
        value.c_str() + m * sizeof(hashed_value_t),
        value.length() % sizeof(hashed_value_t)
    );
    val ^= rem;
    return val;
}


inline hashed_value_t hash_value_merge(hashed_value_t p1, hashed_value_t p2)
{
    return p1 ^ p2;
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

void WriteRecv(hashed_value_t p);
void WriteSend(hashed_value_t p);
void WriteComment(const string &comment);
void WriteEvent(const string &comment);
void WritePhase(const char *phase_name);
void WriteInfo(const string &info);
void WriteTerminate();

}



#endif /* VIZEXEC_LOGWRITER_HPP_ */
