# Speccify
#
# A minimal testing framework that provides some rspecish functionality.
#
#  Features:
#
#  * fast.
#  * nested contexts with 'chained' before and after blocks.
#  * 'obj.should matcher' syntax.
#  * provides an easy way to define matchers. Even complex ones that 
#    are taking args and may receive messages.
#  * 1.9 compatible.
#  * Works well with Rails
#
# There are several examples coming after the framework definition

require 'test/unit'

module Speccify
  module ExampleGroupClassMethods
    attr_accessor :desc, :setup_proc, :teardown_proc
    @desc ||= ""
    
    def setup_proc
      @setup_proc || lambda {}
    end
    
    def teardown_proc
      @teardown_proc || lambda {}
    end

    def before(type = :each, &block)
      raise "unsupported before type: #{type}" unless type == :each
      passed_through_setup = self.setup_proc
      self.setup_proc = lambda { instance_eval(&passed_through_setup);instance_eval(&block) }
      define_method :setup, &self.setup_proc
    end

    def after(type = :each, &block)
      raise "unsupported after type: #{type}" unless type == :each
      passed_through_teardown = self.teardown_proc
      self.teardown_proc = lambda {instance_eval(&block);instance_eval(&passed_through_teardown) }
      define_method :teardown, &self.teardown_proc
    end
    
    def describe desc, &block
      cls = Class.new(self.superclass)
      Object.const_set self.name + desc.to_s.split(/\W+/).map { |s| s.capitalize }.join, cls
      cls.setup_proc = self.setup_proc
      cls.teardown_proc = self.teardown_proc
      cls.desc = self.desc + " " + desc
      cls.tests($1.constantize) if defined?(Rails) && self.name =~ /^(.*Controller)Test/
      cls.class_eval(&block)
    end
    
    def it desc, &block
      self.before {}
      define_method "test_#{desc.gsub(/\W+/, '_').downcase}", &block if block_given?
      self.after {}
    end
  end
  
  module ExampleGroupMethods
    def initialize name
      super
      $current_spec = self
    end
    def default_test
      # test_number -= 1
    end
  end
  
  module Functions
    
    def self.determine_class_name(name)
      name.to_s.split(/\W+/).map { |s| s[0..0].upcase + s[1..-1] }.join 
    end
    
    def self.build_matcher(matcher_name, args, &block)
      match_block = lambda do |actual, matcher|
        block.call(actual, matcher, args)
      end
      body = lambda do |klass|
        @matcher_name = matcher_name.to_s
        def self.matcher_name
          @matcher_name
        end
        
        attr_accessor :positive_msg, :negative_msg, :msgs, :loc
        def initialize match_block
          @match_block = match_block
        end
        
        def method_missing id, *args, &block
          require 'ostruct'
          (self.msgs ||= []) << OpenStruct.new( "name" => id, "args" => args, "block" => block ) 
          self
        end

        def matches? given
          @positive_msg ||= Speccify::Functions::message("#{given} should #{self.class.matcher_name}", "no match", self.class.matcher_name , self.loc || "") 
          @negative_msg ||= Speccify::Functions::message("#{given} should not #{self.class.matcher_name}", "match", self.class.matcher_name , self.loc || "")
          @match_block.call(given, self)
        end
      end
      Class.new(&body).new(match_block)
    end
    
    def self.message(expected, actual, op, location) 
            """
              Expected: #{expected.to_s}
                   got: #{actual.to_s} 
       comparison with: #{op.to_s}
              location: (#{location})
            """
    end
  end

  class OperatorMatcherProxy
    def self.create given, loc, type = true
      body = lambda do |klass|
        define_method(:initialize) do |given|
          @given = given
        end

        ['==', '===', '=~', '>', '>=', '<', '<='].each do |operator|
          define_method(operator) do |actual|
            print_given  = (@given == nil) ? "nil" : @given
            print_actual = (type ? "" : "not ") + (actual.nil? ? "nil" : actual.to_s)
            msg = Speccify::Functions::message(print_actual, print_given, operator, loc) 
            $current_spec.assert(type == @given.send(operator,actual), msg)
          end
        end
      end

      return Class.new(&body).new(given)
    end
  end

  Object.class_eval do
    def should matcher = nil
      if matcher
        matcher.loc = caller[0]
        $current_spec.assert(matcher.matches?(self), matcher.positive_msg)
      else
        OperatorMatcherProxy.create(self,caller[0])
      end
    end

    def should_not matcher = nil
      if matcher
        matcher.loc = caller[0]
        $current_spec.assert(!matcher.matches?(self), matcher.negative_msg)
      else 
        OperatorMatcherProxy.create(self,caller[0], false)
      end
    end
  end
    
  module Extension
    def describe *args, &block
      super_super_class = (Hash === args.last && (args.last[:type] || args.last[:testcase])) || Test::Unit::TestCase 
      super_class = Class.new(super_super_class) do 
        extend ExampleGroupClassMethods
        include ExampleGroupMethods
      end
      cls = Class.new(super_class)
      cnst, desc = args
      Object.const_set Speccify::Functions::determine_class_name(cnst.to_s + "Test"), cls
      cls.desc = String === desc ? desc : cnst.to_s
      cls.class_eval(&block)
    end
    private :describe
    
    def def_matcher(matcher_name, &block)
      self.class.send :define_method, matcher_name do |*args|
        Speccify::Functions::build_matcher(matcher_name, args, &block)
      end
    end
    
    def method_missing(name, *args, &block)
      if (name.to_s =~ /^be_(.+)/)
        Speccify::Functions::build_matcher(name, args) do |given, matcher, args|
          given.send(($1 + "?").to_sym)
        end
      else
        raise NoMethodError.new(name.to_s)
      end
    end
  end # Extension
end # Speccify
include Speccify::Extension

# A few matchers:
def_matcher :be do |given, matcher, args|
  given == args[0]
end

def change(&block)
  Speccify::Functions::build_matcher(:change, []) do |given, matcher, args|
    before = block.call
    given.call
    after = block.call
    comparison = after != before
    if list = matcher.msgs
      comparison = case list[0].name
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

#
### Some examples:
#

# Minimal:
describe "ExampleGroup" do
  it "Example" do
    1.should == 1
  end
end


# With a minimal matcher:
def_matcher :be_nil do |given, matcher, args|
  given == nil
end

describe "Be nil matcher" do
  it "should pass if given is nil" do
    nil.should be_nil
  end
end


# Nested ExampleGroups
describe "first level" do
  
  before do
    $first_level_before ||= 0
    $first_level_before += 1
  end
  
  after do
    $first_level_after ||= 0
    $first_level_after += 1
  end
  
  it "example in first level" do
    $first_level_after.should be_nil
    $first_level_before.should == 1
  end

  describe "second level" do

    before do
      $second_level_before ||= 0
      $second_level_before += 1
    end
    
    after do
      $second_level_after ||= 0
      $second_level_after += 1
    end
    
    it "example in second level" do
      $second_level_after.should == nil
      $first_level_after.should == 1
      $first_level_before.should == 2
      $second_level_before.should == 1
    end
    
    describe "third level" do
      it "second_level_after should have been called now" do
        $second_level_after.should == 1
      end
      
      describe "four" do
        before do
          @var = 1
        end
        describe "Variable defined in parent block " do
          it "should be available without calling before" do
            @var.should_not == nil
          end
        end
      end
    end
  end
end


# A change alike matcher
def_matcher :change do |given, matcher, args|
  raise "callseq: change(lambda {'something here'})" unless Proc === (prok = args[0])
  before = prok.call
  given.call
  before != prok.call
end

describe "Change matcher" do
  before do
    @var = 1
  end
  
  it "should pass if actual was actually changed by given" do
    lambda {@var = 2}.should change(lambda {@var})
  end
  
  it "should not pass if actual was not changed by given" do
    lambda { }.should_not change(lambda {@var})
  end
end