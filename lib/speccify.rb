require 'test/unit'
# No test/unit default_test whining. 
Test::Unit::TestCase.class_eval do 
  def default_test # :nodoc:
    instance_eval { @_result.instance_eval { @run_count ||= 0; @run_count -= 1} if defined?(@_result)}
  end
end

module Speccify
  # These method extend the ExampleGroup as class methods.
  # The methods defined in this module are available
  # inside the example groups ('describe' blocks).
  module ExampleGroupClassMethods
    attr_accessor :desc, :setup_chained, :teardown_chained
    @desc ||= ""
    
    def setup_chained # :nodoc:
      @setup_chained || lambda {}
    end
    
    def teardown_chained # :nodoc:
      @teardown_chained || lambda {}
    end

    # ==Run before each Test.
    # The code in the block attached to this method will be run before each
    # example in all subsequent, eventually nested example groups.
    def before(type = :each, &block)
      raise "unsupported before type: #{type}" unless type == :each
      passed_through_setup = self.setup_chained
      self.setup_chained = lambda { instance_eval(&passed_through_setup);instance_eval(&block) }
      define_method :setup, &self.setup_chained
    end
    
    # ==Run after each Test.
    # The code in the block attached to this method will be run after each
    # example in all subsequent, eventually nested example groups.
    def after(type = :each, &block)
      raise "unsupported after type: #{type}" unless type == :each
      passed_through_teardown = self.teardown_chained
      self.teardown_chained = lambda {instance_eval(&block);instance_eval(&passed_through_teardown) }
      define_method :teardown, &self.teardown_chained
    end
    
    # ==Define an Example Group. 
    # Alike TestCase.
    def describe desc, &block
      modules = self.ancestors
      cls = Class.new(self.superclass) do |klass|
        modules.each {|mod| include mod if (mod.class.to_s == "Module" && !(self < mod))}
      end
      Object.const_set self.name + desc.to_s.split(/\W+/).map { |s| s.capitalize }.join, cls
      cls.setup_chained = self.setup_chained
      cls.teardown_chained = self.teardown_chained
      cls.desc = self.desc + " " + desc
      cls.tests($1.constantize) if defined?(Rails) && self.name =~ /^(.*(Controller|Helper|Mailer))Test/
      cls.class_eval(&block)
    end
    
    # ==Define a test. 
    # Alike 'def test_whatever ..' test definition.
    def it desc, &block
      self.before {}
      desc = Speccify::Functions.make_constantizeable(desc)
      define_method "test_#{desc.gsub(/\W+/, '_').downcase}", &lambda {$current_spec = self; instance_eval(&block)} if block_given?
      self.after {}
    end
  end # ExampleGroupClassMethods

  # == Temporary
  # A temporary module that holds functionality
  # that awaits to be refactored to the right place.
  module Functions   
    def self.determine_class_name(name) #:nodoc:
      name.to_s.split(/\W+/).map { |s| s[0..0].upcase + s[1..-1] }.join 
    end
    
    # A matcher in speccify is a builder method that 
    # returns the right matcher object. 
    # This build_matcher method is the internal interface to the
    # matcher system.
    # (You should use the def_matcher() method to define matchers.)
    #
    # Example:
    #  # The obj.should be_true matcher.
    #  def be_true
    #    Speccify::Functions.build_matcher(:be_true, []) do |given, matcher, args|
    #      given
    #    end
    #  end
    def self.build_matcher(matcher_name, args, &block)
      match_block = lambda do |actual, matcher|
        block.call(actual, matcher, args)
      end
      body = lambda do |klass|
        @matcher_name = matcher_name.to_s
        def self.matcher_name #:nodoc:
          @matcher_name
        end
        
        attr_accessor :positive_msg, :negative_msg, :msgs, :loc
        def initialize match_block #:nodoc:
          @match_block = match_block
        end
        
        def method_missing id, *args, &block   # :nodoc:
          require 'ostruct'
          (self.msgs ||= []) << OpenStruct.new( "name" => id, "args" => args, "block" => block ) 
          self
        end

        def matches? given #:nodoc:
          @positive_msg ||= Speccify::Functions::message(
            "#{given} should #{self.class.matcher_name}", "no match", self.class.matcher_name , self.loc || "") 
          @negative_msg ||= Speccify::Functions::message(
            "#{given} should not #{self.class.matcher_name}", "match", self.class.matcher_name , self.loc || "")
          @match_block.call(given, self)
        end
      end
      Class.new(&body).new(match_block)
    end
    
    def self.make_constantizeable(string)
      return string unless string.class.to_s == "String"
      string = string.gsub(/[^\w\s]/,"").gsub(/^[\d\s]*/,"")
      raise ArgumentError.new(
          "Invalid argument. Must not be empty after removing '\W'-class chars."
      ) if string.gsub(/\s/,"").empty?
      string
    end
    
    def self.message(expected, actual, op, location)  # :nodoc:
            """
              Expected: #{expected.to_s}
                   got: #{actual.to_s} 
       comparison with: #{op.to_s}
              location: (#{location})
            """
    end
  end # Functions

  class OperatorMatcherProxy
    def self.create given, loc, type = true  # :nodoc:
      body = lambda do |klass|
        define_method(:initialize) do |given|
          @given = given
        end

        ['==', '===', '=~', '>', '>=', '<', '<='].each do |operator|
          define_method(operator) do |actual|
            print_given  = (@given == nil) ? "nil" : @given
            print_actual = (type ? "" : "not ") + (actual.nil? ? "nil" : actual.to_s)
            msg = Speccify::Functions::message(print_actual, print_given, operator, loc)
            $current_spec.assert(type == (@given.send(operator,actual) ? true : false), msg)
          end
        end
      end

      return Class.new(&body).new(given)
    end
  end # OperatorMatcherProxy

  class ::Object
    # == obj.should matcher
    # Set an expectation to this object. Can be used in conjunction with
    # an operator (except !=, !~) or a matcher.
    # ===Examples:
    # * 1.should == 1
    # * "asd".should =~ /a/
    # * nil.should be_nil
    def should matcher = nil
      if matcher
        matcher.loc = caller[0]
        $current_spec.assert(matcher.matches?(self), matcher.positive_msg)
      else
        OperatorMatcherProxy.create(self,caller[0])
      end
    end
    # == obj.should_not matcher
    # Set a negative expectation to this object. Can be used in conjunction with
    # an operator (except !=, !~) or a matcher.
    # ===Examples:
    # * 1.should_not == 2
    # * "asd".should_not =~ /b/
    # * 1.should_not be_nil
    def should_not matcher = nil
      if matcher
        matcher.loc = caller[0]
        $current_spec.assert(!matcher.matches?(self), matcher.negative_msg)
      else 
        OperatorMatcherProxy.create(self,caller[0], false)
      end
    end
  end # Object
    
  module Extension
    # == Custom matchers for (almost) FREE
    # 
    # === A simple example first:
    # 
    #   def_matcher :be_nil do |given, matcher, args|      
    #     given.nil?                                       
    #   end                                                
    #   nil.should be_nil                                  
    # *provide def_matcher() the name of your matcher and attach a block 
    # that defines it's behavior.
    # *The return value of the block is a boolean that 
    # actually will be expected (should) or not expected (`should_not`).
    # ==Three arguments are available inside the matcher block:
    # ===given
    # The object that has received the should or `should_not`.
    # === matcher
    # The matcher object. You can set the failure messages as attributes on this object:
    #   matcher.positive_msg = "You can see me if I am applied to should and I return a false value"
    #   matcher.negative_msg = "You can see me if I am applied to should_not and I return a true value"
    # It holds a list of all methods that have been called on the matcher (for chaining):
    #  
    #    obj.should matcher_name.some_method(4,5,6) {"and a block"}.second                                              
    #    def_matcher :matcher_name do |given, matcher, args|                                                            
    #      # this is an ostruct that holds all information about the first method 'some_method'                         
    #      matcher.msgs[0]                                                                                              
    #      # this is an ostruct that holds all information about the second method 'second'                             
    #      matcher.msgs[1]                                                                                              
    #      # this is the name of the first method:                                                                      
    #      matcher.msgs[0].name  #=> :some_method                                                                       
    #      # this is a list of arguments that have been passed to the first method:                                     
    #      matcher.msgs[0].args  #=> [4,5,6]                                                                            
    #      # this is the block that was attached:                                                                       
    #      matcher.msgs[0].block #=> proc {"and a block"}                                                               
    #    end                                                                                                            
    # === args
    # A list of all arguments that have been applied to the matcher. Like the 6 in: 
    #    (3*3).should_not be(6)
    def def_matcher(matcher_name, &block)
      self.class.send :define_method, matcher_name do |*args|
        Speccify::Functions::build_matcher(matcher_name, args, &block)
      end
    end
  end # Extension
  
  module ::Kernel
    def describe *args, &block
      super_class = (Hash === args.last && (args.last[:type] || args.last[:testcase])) || Test::Unit::TestCase 
      super_class.class_eval {extend ExampleGroupClassMethods}
      cls = Class.new(super_class)
      cnst, desc = args
      cnst = Speccify::Functions.make_constantizeable(cnst)
      Object.const_set Speccify::Functions::determine_class_name(cnst.to_s + "Test"), cls
      cls.desc = String === desc ? desc : cnst.to_s
      cls.class_eval(&block)
    end
    private :describe
  end # Kernel
end # Speccify
include Speccify::Extension

# same as should == ...
def_matcher :be do |given, matcher, args|
  given == args[0]
end
# expect obj.eql?(arg)
def_matcher :eql do |given, matcher, args|
  given.eql?(args[0])
end
# expect an exception
def_matcher :raise_error do |given, matcher, args|
  raised = false
  begin
    given.call
  rescue Exception => e
    raised = true
  end
  # todo clean this up
  raised && (args[0].kind_of?(Regexp) ? e.message =~ args[0] : (args[0].nil? ? true : args[0] == e.message))
end
# == lambda {do_something}.should change {something}
# * lambda {var += 1}.should change {var}.by(1)
# * lambda {var += 2}.should change {var}.by_at_least(1)
# * lambda {var += 1}.should change {var}.by_at_most(1)
# * lambda {var += 2}.should change {var}.from(1).to(3) if var = 1
def change(&block)
  Speccify::Functions::build_matcher(:change, []) do |given, matcher, args|
    before = block.call
    given.call
    after = block.call
    comparison = after != before
    if list = matcher.msgs
      comparison = case list[0].name
        # todo provide meaningful messages
      when :by          then (after == before + list[0].args[0] || after == before - list[0].args[0])
      when :by_at_least then (after >= before + list[0].args[0] || after <= before - list[0].args[0])
      when :by_at_most  then (after <= before + list[0].args[0] && after >= before - list[0].args[0])
      when :from        then (before == list[0].args[0]) && (after == list[1].args[0])
      end
    end
    matcher.positive_msg = "given block didn't alter the block attached to change, #{matcher.loc}"
    matcher.negative_msg = "given block did alter the block attached to change, #{matcher.loc}"
    comparison
  end
end

# ==be_*something*
# ===This method_missing acts as a matcher builder method. 
# If a call to be_xyz() reaches this method_missing (say: obj.should be_xyz), 
# a matcher with the name xyz will be built, whose defining property
# is that it returns the value of obj.xyz? for matches?.
def method_missing(name, *args, &block)
  if (name.to_s =~ /^be_(.+)/)
    Speccify::Functions::build_matcher(name, args) do |given, matcher, args|
      given.send(($1 + "?").to_sym)
    end
  else
    raise NoMethodError.new(name.to_s)
  end
end